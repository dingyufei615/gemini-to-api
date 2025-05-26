import asyncio
import os
import time
import uuid
from typing import List, Optional, Dict, Any, AsyncGenerator

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from gemini_webapi import GeminiClient

# Load sensitive credentials from environment variables
Secure_1PSID = os.environ.get("SECURE_1PSID")
Secure_1PSIDTS = os.environ.get("SECURE_1PSIDTS")
GEMINI_PROXY = os.environ.get("GEMINI_PROXY")  # Read proxy configuration

if not Secure_1PSID or not Secure_1PSIDTS:
    print("CRITICAL: Environment variables SECURE_1PSID or SECURE_1PSIDTS not set.")
    # Depending on the desired behavior, you might raise an error here
    # or allow the app to start but GeminiClient will fail to initialize.
    # For now, initialization will be attempted, but will likely fail if these are None.

if GEMINI_PROXY:
    print(f"INFO: Using proxy for Gemini Client: {GEMINI_PROXY}")

# Initialize Gemini Client globally
gemini_client = GeminiClient(Secure_1PSID, Secure_1PSIDTS, proxy=GEMINI_PROXY)
gemini_client_ready = False  # Flag to track Gemini Client readiness

# FastAPI app instance
app = FastAPI(title="Gemini OpenAI-Compatible API", version="0.1.0")


# --- Pydantic Model for Cookie Update ---
class CookieUpdateRequest(BaseModel):
    secure_1papisid: str = Field(..., validation_alias='__Secure-1PAPISID')
    secure_1psidts: str = Field(..., validation_alias='__Secure-1PSIDTS')

    class Config:
        populate_by_name = True

# --- Pydantic Models for OpenAI Compatibility ---

class ChatMessage(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    stream: Optional[bool] = False


# For non-streaming response
class ChatCompletionResponseMessage(BaseModel):
    role: str
    content: str


class ChatCompletionResponseChoice(BaseModel):
    index: int
    message: ChatCompletionResponseMessage
    finish_reason: Optional[str] = "stop"


class UsageInfo(BaseModel):  # Optional: Placeholder if token info becomes available
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None


class ChatCompletionResponse(BaseModel):
    id: str = Field(default_factory=lambda: f"chatcmpl-{uuid.uuid4().hex}")
    object: str = "chat.completion"
    created: int = Field(default_factory=lambda: int(time.time()))
    model: str
    choices: List[ChatCompletionResponseChoice]
    usage: Optional[UsageInfo] = None  # Gemini Web API might not provide token usage easily


# For streaming response
class DeltaMessage(BaseModel):
    role: Optional[str] = None
    content: Optional[str] = None


class ChatCompletionResponseStreamChoice(BaseModel):
    index: int
    delta: DeltaMessage
    finish_reason: Optional[str] = None  # Will be "stop" in the final chunk


class ChatCompletionStreamResponse(BaseModel):
    id: str = Field(default_factory=lambda: f"chatcmpl-{uuid.uuid4().hex}")
    object: str = "chat.completion.chunk"
    created: int = Field(default_factory=lambda: int(time.time()))
    model: str
    choices: List[ChatCompletionResponseStreamChoice]


# --- Pydantic Models for /v1/models endpoint ---

class ModelCard(BaseModel):
    id: str
    object: str = "model"
    created: int = Field(default_factory=lambda: int(time.time()))
    owned_by: str = "google"  # Or a more appropriate owner string


class ModelList(BaseModel):
    object: str = "list"
    data: List[ModelCard]


# --- FastAPI Event Handlers ---
@app.on_event("startup")
async def startup_event():
    global gemini_client_ready
    """Initializes the Gemini Client on application startup."""
    global gemini_client_ready
    if not Secure_1PSID or not Secure_1PSIDTS:
        print("Error: SECURE_1PSID and SECURE_1PSIDTS environment variables must be set to initialize Gemini Client.")
        gemini_client_ready = False
        return

    try:
        print("Initializing Gemini Client...")
        # Parameters for init can be adjusted as needed
        await gemini_client.init(timeout=300, auto_close=False, close_delay=300, auto_refresh=True)
        gemini_client_ready = True
        print("Gemini Client initialized successfully.")
    except Exception as e:
        gemini_client_ready = False
        # Log this error properly in a production scenario
        print(f"CRITICAL: Failed to initialize Gemini Client during startup: {e}")
        # Depending on policy, the app could exit or try to re-initialize later.
        # For now, endpoints will fail if client is not ready.


@app.on_event("shutdown")
async def shutdown_event():
    global gemini_client_ready
    """Closes the Gemini Client on application shutdown."""
    print("Closing Gemini Client...")
    await gemini_client.close()  # Assume close() is safe to call
    gemini_client_ready = False
    print("Gemini Client closed.")


# --- Helper to construct prompt from messages ---
def construct_prompt_from_messages(messages: List[ChatMessage]) -> str:
    """
    Constructs a single string prompt from a list of OpenAI-style messages.
    This basic version concatenates content, prefixing with roles.
    Adjust logic as needed for how Gemini best processes conversational history.
    """
    prompt_parts = []
    system_instruction = None
    for msg in messages:
        role = msg.role.lower()
        if role == "system":
            # Capture the last system message as a prefix/instruction
            system_instruction = msg.content
        elif role == "user":
            content = msg.content
            if system_instruction:
                # Prepend system instruction to the first user message after it.
                prompt_parts.append(f"System Note: {system_instruction}\nUser: {content}")
                system_instruction = None  # Consume it
            else:
                prompt_parts.append(f"User: {content}")
        elif role == "assistant":
            prompt_parts.append(f"Assistant: {msg.content}")
        else:  # Unknown role
            prompt_parts.append(f"{msg.role.capitalize()}: {msg.content}")

    return "\n\n".join(prompt_parts)


# --- API Endpoints ---

# Static list of models based on README.md
# Note: "created" timestamp will be dynamic based on when ModelCard is instantiated.
# "owned_by" is set to "google" as a general owner for these models.
AVAILABLE_MODELS = [
    ModelCard(id="unspecified"),  # Default model
    ModelCard(id="gemini-2.0-flash"),
    ModelCard(id="gemini-2.0-flash-thinking"),  # Experimental
    ModelCard(id="gemini-2.5-flash"),
    ModelCard(id="gemini-2.5-pro"),  # Daily usage limit
    ModelCard(id="gemini-2.5-exp-advanced"),  # Requires Gemini Advanced
    ModelCard(id="gemini-2.0-exp-advanced"),  # Requires Gemini Advanced
]


@app.post("/api/cookies")
async def update_cookies(cookie_data: CookieUpdateRequest):
    """
    更新Gemini认证凭据的接口
    """
    global Secure_1PSID, Secure_1PSIDTS, gemini_client, gemini_client_ready
    
    # 安全验证建议：生产环境应添加API Key验证
    # if not verify_api_key(request.headers.get("Authorization")):
    #     raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        # 关闭现有客户端连接
        if gemini_client_ready:
            await gemini_client.close()
            print("Closed existing Gemini client connection")

        # 更新环境变量
        os.environ["SECURE_1PSID"] = cookie_data.secure_1papisid
        os.environ["SECURE_1PSIDTS"] = cookie_data.secure_1psidts
        Secure_1PSID = cookie_data.secure_1papisid
        Secure_1PSIDTS = cookie_data.secure_1psidts

        # 重新初始化客户端
        gemini_client = GeminiClient(Secure_1PSID, Secure_1PSIDTS, proxy=GEMINI_PROXY)
        await gemini_client.init(
            timeout=300,
            auto_close=False,
            close_delay=300,
            auto_refresh=True
        )
        gemini_client_ready = True
        print("Successfully updated cookies and reinitialized Gemini client")

        return {"status": "success", "message": "Cookies updated successfully"}

    except Exception as e:
        gemini_client_ready = False
        print(f"Failed to update cookies: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update cookies: {str(e)}"
        )

@app.get("/v1/models", response_model=ModelList)
async def list_models():
    """
    Lists the currently available models.
    Based on OpenAI's /v1/models endpoint.
    """
    return ModelList(data=AVAILABLE_MODELS)


@app.post("/v1/chat/completions", response_model=None)  # response_model handled by Streaming or direct return
async def create_chat_completion(request: ChatCompletionRequest,
                                 http_request: Request):  # http_request for client disconnect check
    """
    OpenAI-compatible chat completion endpoint.
    Supports both streaming and non-streaming responses.
    """
    global gemini_client_ready
    if not gemini_client_ready:  # Basic check using our flag
        print("Error: Gemini client session not active or closed.")
        raise HTTPException(status_code=503,
                            detail="Gemini client is not initialized or session closed. Please try again shortly.")

    if not request.messages:
        raise HTTPException(status_code=400, detail="No messages provided in the request.")

    # Construct a single prompt string from the messages array.
    # `gemini-webapi`'s `generate_content` expects a single prompt.
    # `ChatSession` can handle history, but mapping OpenAI's `messages` array to it perfectly
    # for *every* call requires careful state management if we were to use `ChatSession` directly here
    # for each turn in `request.messages`. Using `generate_content` with a combined prompt is simpler
    # for a stateless OpenAI-like API call.
    final_prompt = construct_prompt_from_messages(request.messages)

    if not final_prompt:  # Ensure there's something to send
        raise HTTPException(status_code=400, detail="Failed to construct a valid prompt from messages.")

    try:
        # Using generate_content for a stateless call based on the full context in messages.
        # The model string from the request is passed directly.
        gemini_api_response = await gemini_client.generate_content(
            prompt=final_prompt,
            model=request.model
        )

        gemini_response_text = ""
        if gemini_api_response and hasattr(gemini_api_response, 'text'):
            gemini_response_text = gemini_api_response.text
        elif gemini_api_response and isinstance(gemini_api_response, str):  # Fallback if API changes
            gemini_response_text = gemini_api_response
        else:
            # Log unexpected response structure
            print(f"Warning: Unexpected response structure from Gemini generate_content: {gemini_api_response}")
            # Depending on strictness, could raise 500 or return empty.
            # For robustness, return empty or a standard error message.
            gemini_response_text = "Error: Received no valid text content from Gemini."


    except Exception as e:
        print(f"Error during Gemini API call: {type(e).__name__} - {e}")
        # Consider logging the full traceback here for debugging
        raise HTTPException(status_code=500, detail=f"Error communicating with Gemini API: {str(e)}")

    response_id = f"chatcmpl-{uuid.uuid4().hex}"
    created_time = int(time.time())

    if request.stream:
        async def stream_generator() -> AsyncGenerator[str, None]:
            try:
                # Send content chunk
                stream_choice = ChatCompletionResponseStreamChoice(
                    index=0,
                    delta=DeltaMessage(role="assistant", content=gemini_response_text),
                    finish_reason=None
                )
                response_chunk = ChatCompletionStreamResponse(
                    id=response_id,
                    object="chat.completion.chunk",
                    created=created_time,
                    model=request.model,
                    choices=[stream_choice]
                )
                yield f"data: {response_chunk.model_dump_json(exclude_none=True)}\n\n"

                # Send final chunk indicating completion
                final_delta = DeltaMessage()  # Empty delta for final chunk
                final_choice = ChatCompletionResponseStreamChoice(
                    index=0,
                    delta=final_delta,
                    finish_reason="stop"
                )
                final_response_chunk = ChatCompletionStreamResponse(
                    id=response_id,
                    object="chat.completion.chunk",
                    created=created_time,  # Should be same timestamp or new one? OpenAI uses same.
                    model=request.model,
                    choices=[final_choice]
                )
                yield f"data: {final_response_chunk.model_dump_json(exclude_none=True)}\n\n"
                yield "data: [DONE]\n\n"
            except asyncio.CancelledError:
                print("Stream cancelled by client.")
                # Perform any necessary cleanup
            except Exception as e_stream:
                print(f"Error during stream generation: {e_stream}")
                # Potentially yield an error message in the stream if the protocol supports it,
                # or just log and ensure the stream closes.
                # For text/event-stream, abruptly ending might be the only option here.

        return StreamingResponse(stream_generator(), media_type="text/event-stream")
    else:
        # Non-streaming response
        return ChatCompletionResponse(
            id=response_id,
            created=created_time,
            model=request.model,
            choices=[
                ChatCompletionResponseChoice(
                    index=0,
                    message=ChatCompletionResponseMessage(role="assistant", content=gemini_response_text),
                    finish_reason="stop"
                )
            ],
            usage=UsageInfo()  # Placeholder for usage, as gemini-webapi may not provide it
        )
