import { useState, useRef, useEffect } from "react";
import { Send, Bot, User } from "lucide-react";
import ReactMarkdown from "react-markdown";
import "../Chat.css";

const Chat = ({ onClose }) => {
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content: "Cześć! Jestem asystentem komunikacji miejskiej w Łodzi. Jak mogę Ci pomóc?",
    },
  ]);
  const [inputValue, setInputValue] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const sendMessage = async () => {
    if (!inputValue.trim() || isLoading) return;

    const userMessage = {
      role: "user",
      content: inputValue.trim(),
    };

    // Dodaj wiadomość użytkownika od razu
    setMessages((prev) => [...prev, userMessage]);
    setInputValue("");
    setIsLoading(true);

    try {
      // Przygotuj historię konwersacji (wszystkie poprzednie wiadomości)
      // Konwertuj historię do formatu oczekiwanego przez API
      const conversationHistory = [...messages, userMessage].map((msg) => ({
        role: msg.role === "assistant" ? "assistant" : "user",
        content: msg.content,
      }));

      const response = await fetch("http://127.0.0.1:8000/chat", {
        method: "POST",
        headers: {
          "accept": "application/json",
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          messages: conversationHistory,
          model: "gpt-5.1",
          temperature: 0.7,
          include_traffic_info: true,
        }),
      });

      if (!response.ok) {
        throw new Error("Błąd podczas komunikacji z API");
      }

      const data = await response.json();
      
      // Dodaj odpowiedź asystenta
      // API zwraca ChatResponse z polem "message"
      const assistantMessage = {
        role: "assistant",
        content: data.message || data.response || "Przepraszam, nie udało się uzyskać odpowiedzi.",
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      console.error("Error:", error);
      const errorMessage = {
        role: "assistant",
        content: "Przepraszam, wystąpił błąd podczas komunikacji. Spróbuj ponownie.",
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div className="chat-container">
      <div className="chat-header">
        <div className="chat-header-content">
          <Bot size={24} className="chat-header-icon" />
          <h2 className="chat-header-title">Asystent MPK</h2>
        </div>
        <button className="chat-close-btn" onClick={onClose}>
          ✕
        </button>
      </div>

      <div className="chat-messages">
        {messages.map((message, index) => (
          <div
            key={index}
            className={`chat-message ${message.role === "user" ? "user-message" : "assistant-message"}`}
          >
            <div className="chat-message-avatar">
              {message.role === "user" ? (
                <User size={20} />
              ) : (
                <Bot size={20} />
              )}
            </div>
            <div className="chat-message-content">
              {message.role === "assistant" ? (
                <div className="chat-message-text">
                  <ReactMarkdown
                    components={{
                      p: ({ children }) => <p className="markdown-p">{children}</p>,
                      strong: ({ children }) => <strong className="markdown-strong">{children}</strong>,
                      em: ({ children }) => <em className="markdown-em">{children}</em>,
                      ul: ({ children }) => <ul className="markdown-ul">{children}</ul>,
                      ol: ({ children }) => <ol className="markdown-ol">{children}</ol>,
                      li: ({ children }) => <li className="markdown-li">{children}</li>,
                      a: ({ href, children }) => (
                        <a href={href} target="_blank" rel="noopener noreferrer" className="markdown-link">
                          {children}
                        </a>
                      ),
                      code: ({ children }) => <code className="markdown-code">{children}</code>,
                      blockquote: ({ children }) => <blockquote className="markdown-blockquote">{children}</blockquote>,
                    }}
                  >
                    {message.content}
                  </ReactMarkdown>
                </div>
              ) : (
                <div className="chat-message-text">{message.content}</div>
              )}
            </div>
          </div>
        ))}
        {isLoading && (
          <div className="chat-message assistant-message">
            <div className="chat-message-avatar">
              <Bot size={20} />
            </div>
            <div className="chat-message-content">
              <div className="chat-message-text typing-indicator">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="chat-input-container">
        <input
          ref={inputRef}
          type="text"
          className="chat-input"
          placeholder="Napisz wiadomość..."
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyPress={handleKeyPress}
          disabled={isLoading}
        />
        <button
          className="chat-send-btn"
          onClick={sendMessage}
          disabled={isLoading || !inputValue.trim()}
        >
          <Send size={20} />
        </button>
      </div>
    </div>
  );
};

export default Chat;

