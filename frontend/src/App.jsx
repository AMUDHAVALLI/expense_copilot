import React, { useState, useRef, useEffect } from 'react';
import { 
  Send, Bot, User, Loader2, Sparkles, Database, 
  RotateCcw, Trash2, Calendar, TrendingUp, CheckCircle2, 
  ShoppingBag, ArrowDownCircle, PieChart as ChartIcon
} from 'lucide-react';
import DynamicChart from './components/DynamicChart';
import TooltipPicker from './components/TooltipPicker';

export default function App() {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      text: "👋 **Welcome to Expense Copilot!**\n\nI am connected to your live **PostgreSQL** database. Here is what I can do for your demo:\n\n1. 🛒 **Add Daily Expenses**: *'Milk 45, Vegetables 120 and Bread 35'*\n2. 🔍 **Zero-Hallucination Queries**: *'Calculate today dairy amount'* (Queries and sums strictly Dairy)\n3. 📅 **Future Planning**: *'Plan ₹4500 for Bike Insurance on Dec 15'*\n4. 📊 **On-Demand Charts**: *'Show pie chart of expenses'* or *'Show bar chart of future commitments'*",
      chart: null,
      suggestions: [
        {
          question: "Calculate today dairy amount",
          tooltip: "Queries only Dairy records from PostgreSQL without hallucination"
        },
        {
          question: "Show pie chart of my expenses",
          tooltip: "Renders on-demand interactive visualization (Pie, Bar, Line)"
        },
        {
          question: "What did I spend today?",
          tooltip: "Aggregates all recorded spending for today"
        },
        {
          question: "Show future planned expenses",
          tooltip: "Lists upcoming scheduled commitments from PostgreSQL"
        }
      ]
    }
  ]);

  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState({
    today_total: 0,
    future_total: 0,
    total_records: 0,
    database: 'PostgreSQL'
  });
  const [notification, setNotification] = useState(null);
  const chatBottomRef = useRef(null);

  // Fetch summary stats from PostgreSQL
  const refreshStats = async () => {
    try {
      const res = await fetch('http://127.0.0.1:8000/api/summary');
      if (res.ok) {
        const data = await res.json();
        setStats(data);
      }
    } catch {
      // Backend not reached yet
    }
  };

  useEffect(() => {
    refreshStats();
  }, []);

  // Auto-scroll on new message
  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  // Seed clean demo data (for interview presentation)
  const handleSeedData = async () => {
    setLoading(true);
    try {
      const res = await fetch('http://127.0.0.1:8000/api/seed', { method: 'POST' });
      if (res.ok) {
        await refreshStats();
        setNotification('✅ Realistic demo data loaded into PostgreSQL!');
        setTimeout(() => setNotification(null), 3000);
        setMessages((prev) => [
          ...prev,
          {
            role: 'assistant',
            text: "✅ **Demo data seeded successfully into PostgreSQL!**\n\n• Recorded today's expenses across Dairy, Veggies, Food, Transport.\n• Stored planned future expenses (Bike Insurance & Broadband Wifi).\n\nTry clicking **'Calculate today dairy amount'** or **'Show pie chart of my expenses'** below.",
            chart: null,
            suggestions: [
              { question: "Calculate today dairy amount", tooltip: "Calculates Dairy items: Milk + Paneer & Curd" },
              { question: "Show pie chart of my expenses", tooltip: "Visualizes the seeded expenses in an interactive chart" },
              { question: "Show future planned expenses", tooltip: "Displays planned future commitments" }
            ]
          }
        ]);
      }
    } catch (err) {
      setNotification('⚠️ Failed to seed data.');
    } finally {
      setLoading(false);
    }
  };

  // Clear chat view
  const handleClearChat = () => {
    setMessages([
      {
        role: 'assistant',
        text: "🧹 **Chat cleared.** Ready for your next query!",
        chart: null,
        suggestions: [
          { question: "Calculate today dairy amount", tooltip: "Calculates Dairy items strictly from PostgreSQL" },
          { question: "Show pie chart of my expenses", tooltip: "Generates an interactive chart" },
          { question: "What did I spend today?", tooltip: "Summarizes today's total spend" }
        ]
      }
    ]);
  };

  const handleSendMessage = async (textToSend) => {
    const message = textToSend || input;
    if (!message || !message.trim() || loading) return;

    const newMessages = [...messages, { role: 'user', text: message }];
    setMessages(newMessages);
    setInput('');
    setLoading(true);

    try {
      const res = await fetch('http://127.0.0.1:8000/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message })
      });

      if (!res.ok) throw new Error(`HTTP ${res.status}`);

      const data = await res.json();
      await refreshStats();

      setMessages([
        ...newMessages,
        {
          role: 'assistant',
          text: data.reply,
          chart: data.chart,
          suggestions: data.suggestions
        }
      ]);
    } catch (err) {
      setMessages([
        ...newMessages,
        {
          role: 'assistant',
          text: `⚠️ **Could not connect to backend server**: ${err.message}.\n\nPlease ensure FastAPI is running on http://127.0.0.1:8000.`,
          chart: null,
          suggestions: [
            { question: "Calculate today dairy amount", tooltip: "Retry querying dairy from PostgreSQL" }
          ]
        }
      ]);
    } finally {
      setLoading(false);
    }
  };

  // Render markdown bold and line breaks
  const renderFormattedText = (rawText) => {
    if (!rawText) return null;
    const lines = rawText.split('\n');
    return lines.map((line, idx) => {
      const parts = line.split(/(\*\*.*?\*\*)/g);
      return (
        <p key={idx} className={line.trim() === '' ? 'h-2' : 'my-0.5'}>
          {parts.map((part, pIdx) => {
            if (part.startsWith('**') && part.endsWith('**')) {
              return (
                <strong key={pIdx} className="font-semibold text-slate-900">
                  {part.slice(2, -2)}
                </strong>
              );
            }
            if (part.startsWith('*') && part.endsWith('*')) {
              return (
                <em key={pIdx} className="italic text-indigo-700">
                  {part.slice(1, -1)}
                </em>
              );
            }
            return part;
          })}
        </p>
      );
    });
  };

  // Quick Action Buttons
  const quickActions = [
    { label: "🥛 Dairy", query: "Calculate today dairy amount", tip: "Query Dairy total" },
    { label: "🥦 Veggies", query: "How much spent on vegetables today?", tip: "Query Vegetables total" },
    { label: "🍔 Food", query: "How much did I spend on food today?", tip: "Query Food & Dining total" },
    { label: "🚗 Transport", query: "How much spent on transport today?", tip: "Query Transport total" },
    { label: "📅 Future", query: "Show future planned expenses", tip: "View upcoming commitments" },
    { label: "📊 Chart", query: "Show pie chart of my expenses", tip: "Render dynamic visual chart" }
  ];

  return (
    <div className="flex h-screen w-full bg-slate-100 text-slate-800 flex-col items-center justify-center p-0 sm:p-4">
      {/* 100% Chat Window Container */}
      <div className="w-full max-w-4xl h-full sm:h-[96vh] flex flex-col bg-white sm:border sm:border-slate-200 sm:rounded-2xl shadow-xl overflow-hidden">
        
        {/* Interactive Top Bar */}
        <header className="px-5 py-3 border-b border-slate-200 bg-white flex flex-wrap items-center justify-between gap-3 shrink-0 shadow-xs">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-indigo-600 via-indigo-500 to-pink-500 flex items-center justify-center shadow-md shadow-indigo-100">
              <Bot className="w-5 h-5 text-white" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-sm font-bold text-slate-900 tracking-wide">Expense Copilot</h1>
                <span className="flex items-center gap-1 text-[10px] bg-emerald-50 text-emerald-700 px-2 py-0.5 rounded-full border border-emerald-200 font-medium">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
                  PostgreSQL Live
                </span>
              </div>
              <p className="text-[11px] text-slate-500">Autonomous Financial Agent • Zero-Hallucination DB Analytics</p>
            </div>
          </div>

          {/* Live Dynamic Stats Badges & Demo Controls */}
          <div className="flex items-center gap-2">
            <div className="hidden sm:flex items-center gap-2 bg-slate-50 px-3 py-1.5 rounded-xl border border-slate-200 text-xs">
              <span className="text-slate-500">Today:</span>
              <strong className="text-indigo-600 font-semibold">₹{stats.today_total.toFixed(2)}</strong>
              <span className="text-slate-300">|</span>
              <span className="text-slate-500">Planned:</span>
              <strong className="text-emerald-600 font-semibold">₹{stats.future_total.toFixed(2)}</strong>
            </div>

            {/* Seed Demo Button (Great for interview demos) */}
            <button
              onClick={handleSeedData}
              title="Reset and load clean demo records into PostgreSQL"
              className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-medium bg-indigo-50 hover:bg-indigo-100 text-indigo-700 border border-indigo-200 transition-all cursor-pointer active:scale-95"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span className="hidden md:inline">Seed Demo</span>
            </button>

            {/* Clear Chat Button */}
            <button
              onClick={handleClearChat}
              title="Clear chat messages"
              className="flex items-center gap-1 p-1.5 rounded-lg text-xs font-medium text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-all cursor-pointer"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          </div>
        </header>

        {/* Temporary Notification Banner */}
        {notification && (
          <div className="bg-emerald-50 border-b border-emerald-200 text-emerald-800 text-xs py-1.5 px-4 text-center font-medium animate-in fade-in">
            {notification}
          </div>
        )}

        {/* Message Stream */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-5 bg-slate-50/50">
          {messages.map((msg, index) => {
            const isUser = msg.role === 'user';
            return (
              <div
                key={index}
                className={`flex gap-3 ${isUser ? 'justify-end' : 'justify-start'}`}
              >
                {!isUser && (
                  <div className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center shrink-0 mt-1 shadow-xs">
                    <Bot className="w-4 h-4 text-white" />
                  </div>
                )}

                <div
                  className={`max-w-[90%] sm:max-w-[80%] rounded-2xl p-4 text-sm leading-relaxed shadow-xs transition-all ${
                    isUser
                      ? 'bg-indigo-600 text-white rounded-br-none shadow-md shadow-indigo-100'
                      : 'bg-white text-slate-800 border border-slate-200 rounded-tl-none shadow-sm'
                  }`}
                >
                  <div className="space-y-1">{renderFormattedText(msg.text)}</div>

                  {/* Dynamic Recharts Visualization with Live Tab Switcher */}
                  {msg.chart && <DynamicChart chart={msg.chart} />}

                  {/* Suggestion Prompts with Radix Tooltips */}
                  {msg.suggestions && msg.suggestions.length > 0 && (
                    <div className="mt-3.5 pt-3 border-t border-slate-100">
                      <div className="flex items-center gap-1.5 text-[11px] text-slate-500 mb-1.5 font-medium">
                        <ArrowDownCircle className="w-3.5 h-3.5 text-indigo-600" />
                        <span>Quick Prompts (Hover for Tooltip / Click to Ask):</span>
                      </div>
                      <TooltipPicker
                        suggestions={msg.suggestions}
                        onSelect={(question) => handleSendMessage(question)}
                      />
                    </div>
                  )}
                </div>

                {isUser && (
                  <div className="w-8 h-8 rounded-lg bg-slate-300 flex items-center justify-center shrink-0 mt-1 shadow-xs">
                    <User className="w-4 h-4 text-slate-700" />
                  </div>
                )}
              </div>
            );
          })}

          {loading && (
            <div className="flex gap-3 justify-start items-center text-slate-500 text-xs py-2">
              <div className="w-8 h-8 rounded-lg bg-indigo-50 border border-indigo-200 flex items-center justify-center">
                <Loader2 className="w-4 h-4 text-indigo-600 animate-spin" />
              </div>
              <span className="animate-pulse">Querying PostgreSQL database...</span>
            </div>
          )}

          <div ref={chatBottomRef} />
        </div>

        {/* Interactive Quick-Filter Category Bar */}
        <div className="px-4 py-2 bg-slate-50 border-t border-slate-200/80 flex items-center gap-2 overflow-x-auto scrollbar-none">
          <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider shrink-0 flex items-center gap-1">
            ⚡ Quick Filters:
          </span>
          {quickActions.map((qa, i) => (
            <button
              key={i}
              type="button"
              onClick={() => handleSendMessage(qa.query)}
              title={qa.tip}
              className="shrink-0 px-2.5 py-1 rounded-full text-xs font-medium bg-white hover:bg-indigo-50 text-slate-700 hover:text-indigo-700 border border-slate-200 hover:border-indigo-300 shadow-2xs transition-all cursor-pointer active:scale-95"
            >
              {qa.label}
            </button>
          ))}
        </div>

        {/* Input Bar */}
        <div className="p-3 sm:p-4 bg-white border-t border-slate-200 shrink-0">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSendMessage();
            }}
            className="flex items-center gap-2"
          >
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="e.g. 'Calculate today dairy amount' or 'Spent 45 on milk and 90 on veggies'..."
              className="flex-1 bg-slate-50 border border-slate-300 text-slate-900 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-indigo-600 focus:bg-white focus:ring-1 focus:ring-indigo-600 transition-all placeholder:text-slate-400"
            />
            <button
              type="submit"
              disabled={loading || !input.trim()}
              className="bg-indigo-600 hover:bg-indigo-700 disabled:opacity-40 disabled:cursor-not-allowed text-white font-medium px-4 py-3 rounded-xl transition-all flex items-center justify-center shadow-md shadow-indigo-100 cursor-pointer"
            >
              <Send className="w-4 h-4" />
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
