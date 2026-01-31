import {
  useVoiceAssistant,
  BarVisualizer,
  useTrackTranscription,
  useLocalParticipant,
  DisconnectButton,
  TrackToggle,
} from "@livekit/components-react";
import { Track } from "livekit-client";
import { useEffect, useState, useRef } from "react";
import "./SimpleVoiceAssistant.css";

const Message = ({ type, text }) => {
  return (
    <div className={`message message-${type}`}>
      <div className="message-avatar">
        {type === "agent" ? "🤖" : "👤"}
      </div>
      <div className="message-content">
        <span className="message-label">{type === "agent" ? "Agent" : "You"}</span>
        <p className="message-text">{text}</p>
      </div>
    </div>
  );
};

// Custom icons
const MicIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/>
    <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
    <line x1="12" x2="12" y1="19" y2="22"/>
  </svg>
);

const MicOffIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="2" x2="22" y1="2" y2="22"/>
    <path d="M18.89 13.23A7.12 7.12 0 0 0 19 12v-2"/>
    <path d="M5 10v2a7 7 0 0 0 12 5"/>
    <path d="M15 9.34V5a3 3 0 0 0-5.68-1.33"/>
    <path d="M9 9v3a3 3 0 0 0 5.12 2.12"/>
    <line x1="12" x2="12" y1="19" y2="22"/>
  </svg>
);

const DisconnectIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M10.68 13.31a16 16 0 0 0 3.41 2.6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7 2 2 0 0 1 1.72 2v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.42 19.42 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.63A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91"/>
    <line x1="22" x2="2" y1="2" y2="22"/>
  </svg>
);

const SimpleVoiceAssistant = () => {
  const { state, audioTrack, agentTranscriptions } = useVoiceAssistant();
  const localParticipant = useLocalParticipant();
  const { segments: userTranscriptions } = useTrackTranscription({
    publication: localParticipant.microphoneTrack,
    source: Track.Source.Microphone,
    participant: localParticipant.localParticipant,
  });

  const [messages, setMessages] = useState([]);
  const conversationRef = useRef(null);

  useEffect(() => {
    const allMessages = [
      ...(agentTranscriptions?.map((t) => ({ ...t, type: "agent" })) ?? []),
      ...(userTranscriptions?.map((t) => ({ ...t, type: "user" })) ?? []),
    ].sort((a, b) => a.firstReceivedTime - b.firstReceivedTime);
    setMessages(allMessages);
  }, [agentTranscriptions, userTranscriptions]);

  useEffect(() => {
    if (conversationRef.current) {
      conversationRef.current.scrollTop = conversationRef.current.scrollHeight;
    }
  }, [messages]);

  const getStateLabel = () => {
    switch (state) {
      case "listening": return "Listening...";
      case "thinking": return "Processing...";
      case "speaking": return "Speaking...";
      default: return "Ready";
    }
  };

  return (
    <div className="voice-assistant-container">
      <div className="status-indicator">
        <div className={`status-dot ${state}`}></div>
        <span className="status-text">{getStateLabel()}</span>
      </div>
      
      <div className="visualizer-container">
        <div className="visualizer-glow"></div>
        <BarVisualizer state={state} barCount={5} trackRef={audioTrack} />
      </div>

      <div className="conversation" ref={conversationRef}>
        {messages.length === 0 ? (
          <div className="empty-state">
            <p>Start speaking to begin the conversation</p>
          </div>
        ) : (
          messages.map((msg, index) => (
            <Message key={msg.id || index} type={msg.type} text={msg.text} />
          ))
        )}
      </div>

      <div className="control-section">
        <div className="custom-controls">
          <TrackToggle source={Track.Source.Microphone} className="control-btn mic-btn">
            {({ enabled }) => (enabled ? <MicIcon /> : <MicOffIcon />)}
          </TrackToggle>
          <DisconnectButton className="control-btn disconnect-btn">
            <DisconnectIcon />
          </DisconnectButton>
        </div>
      </div>
    </div>
  );
};

export default SimpleVoiceAssistant;