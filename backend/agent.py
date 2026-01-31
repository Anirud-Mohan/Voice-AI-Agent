from livekit.agents import (
    AutoSubscribe,
    JobContext,
    WorkerOptions,
    cli,
    llm,
    AgentSession,
    Agent,
)
from livekit.plugins import google
from api import AssistantFnc
from prompts import WELCOME_MESSAGE, INSTRUCTIONS, LOOKUP_VIN_MESSAGE
from guardrails import GuardrailStatus
from dotenv import load_dotenv
import logging
import asyncio

load_dotenv()
logger = logging.getLogger("voice-agent")

async def entrypoint(ctx: JobContext):
    await ctx.connect(auto_subscribe=AutoSubscribe.SUBSCRIBE_ALL)
    participant = await ctx.wait_for_participant()

    user_identifier = participant.identity or f"web-{participant.sid}"
    display_name = participant.name or user_identifier
    logger.info(f"User connected: {user_identifier}, display_name: {display_name}")

    # Build personalized instructions with user's name
    personalized_welcome = f"Hi {display_name}! {WELCOME_MESSAGE}"
    personalized_instructions = f"""{INSTRUCTIONS}

## GREETING:
When starting the conversation, greet the user warmly by saying: "{personalized_welcome}"
"""

    model = google.realtime.RealtimeModel(
        model="gemini-2.5-flash-native-audio-preview-12-2025", 
        voice="Puck", 
        temperature=0.4,
        instructions=personalized_instructions,
    )

    assistant_fnc = AssistantFnc()
    # Initialize session management
    session_id = assistant_fnc.set_session(user_identifier, identifier_type="web")
    logger.info(f"Session initialized: {session_id}")
    
    # Log the welcome message
    assistant_fnc.log_message("assistant", personalized_welcome)
    
    tools = llm.find_function_tools(assistant_fnc)
    agent = Agent(
        instructions=personalized_instructions,
        tools=tools,
    )

    session = AgentSession(llm=model)
    await session.start(room=ctx.room, agent=agent)
    logger.info("Session started")

    @session.on('user_speech_committed')
    def on_user_speech_committed(msg: llm.ChatMessage):        
        logger.info(f"user_speech_committed fired, content={msg.content[:50] if msg.content else 'None'}...")
            
        if isinstance(msg.content, list):
            msg.content = '\n'.join('[image]' if isinstance(x, llm.ChatImage) else x for x in msg.content)

        user_text = msg.content if isinstance(msg.content, str) else str(msg.content)
        
        # Ignore empty/whitespace transcripts
        if not user_text or not user_text.strip():
            return

        # Apply guardrails to user input
        guardrail_result = assistant_fnc.check_input(user_text)
        
        # Log user message
        assistant_fnc.log_message("user", user_text)
        
        if guardrail_result.status == GuardrailStatus.BLOCKED:
            # Input is blocked - inject guardrail message
            logger.warning(f"Input blocked by guardrails: {user_text[:50]}...")
            session.conversation.item.create(
                llm.ChatMessage(
                    role='assistant',
                    content=guardrail_result.message
                )
            )
            assistant_fnc.log_message("assistant", guardrail_result.message)
            session.response.create()
            return
        
        if guardrail_result.status == GuardrailStatus.REDIRECTED:
            logger.info(f"Input redirected by guardrails: {user_text[:50]}...")
            session.conversation.item.create(
                llm.ChatMessage(
                    role='assistant',
                    content=guardrail_result.message
                )
            )
            assistant_fnc.log_message("assistant", guardrail_result.message)
            session.response.create()
            return

        # Input passed guardrails - proceed normally
        if assistant_fnc.has_car():
            handle_query(msg)
        else:
            find_profile(msg)

    def find_profile(msg: llm.ChatMessage):
        session.conversation.item.create(
            llm.ChatMessage(
                role='system',
                content=LOOKUP_VIN_MESSAGE(msg)
            )
        )
        session.response.create()

    def handle_query(msg: llm.ChatMessage):
        session.conversation.item.create(
            llm.ChatMessage(
                role='user',
                content=msg.content
            )
        )
        session.response.create()
    
    # Trigger welcome (returns SpeechHandle, non-blocking)
    logger.info("Triggering welcome reply...")
    session.generate_reply()
    logger.info("Welcome triggered")

if __name__ == '__main__':
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))