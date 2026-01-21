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
from dotenv import load_dotenv
import logging

load_dotenv()
logger = logging.getLogger("voice-agent")

async def entrypoint(ctx: JobContext):
    await ctx.connect(auto_subscribe=AutoSubscribe.SUBSCRIBE_ALL)
    await ctx.wait_for_participant()

    # 1. Initialize the Model
    # Remove 'modalities' to use the safe defaults (Audio + Text).
    # Explicitly set the model to a known working version.
    model = google.realtime.RealtimeModel(
        model="gemini-2.5-flash-native-audio-preview-12-2025", 
        voice="Puck", 
        temperature=0.4,
        instructions=INSTRUCTIONS,
    )

    # 2. Define Initial Chat Context (The Welcome Message)
    # We create a ChatContext object and append the welcome message here.
    initial_ctx = llm.ChatContext()
    initial_ctx.add_message(
        role="assistant",
        content=WELCOME_MESSAGE,
    )

    # 3. Define the Agent
    assistant_fnc = AssistantFnc()
    tools = llm.find_function_tools(assistant_fnc)
    # Pass the initial_ctx here. The Agent handles the history now.
    agent = Agent(
        instructions=INSTRUCTIONS,
        tools=tools,
        # tools=llm.find_function_tools([assistant_fnc.create_car, assistant_fnc.get_car_details, assistant_fnc.has_car, assistant_fnc.lookup_car]),
        chat_ctx=initial_ctx, 
    )

    # 4. Start the Session
    session = AgentSession(llm=model)
    await session.start(room=ctx.room, agent=agent)
    
    # 5. Trigger the Reply
    # This will make the agent speak the welcome message (or acknowledge it).
    await session.generate_reply()


    @session.on('user_speeech_committed')
    def on_user_speech_committed(msg: llm.ChatMessage):
        if isinstance(msg.content, list):
            msg.content = '\n'.join('[image]' if isinstance(x, llm.ChatImage) else x for x in msg)

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

if __name__ == '__main__':
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))