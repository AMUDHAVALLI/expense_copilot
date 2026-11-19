import React, { useState, useRef, useEffect } from 'react';
import { 
  Send, Bot, User, Loader2, Sparkles, 
  Calendar, TrendingUp, CheckCircle2, 
  ShoppingBag, ArrowDownCircle, PieChart as ChartIcon,
  Wallet, Landmark, Brain
} from 'lucide-react';
import DynamicChart from './components/DynamicChart';
import TooltipPicker from './components/TooltipPicker';

const API_BASE = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '');

export default function App() {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      text: "👋 **Welcome to Expense Copilot!**\n\nI am your autonomous financial assistant connected to your live cloud ledger. Here is what I can do for you:\n\n1. 🛒 **Track Multiple Expenses**: *'Milk 45, Vegetables 120 and Bread 35'*\n2. 🔍 **Precise Category Calculations**: *'Calculate today dairy amount'* (Strictly filters and sums Dairy items without hallucination)\n3. 🔮 **Predictive Forecasting**: *'Predict my next month expenses'* (Forecasts monthly burn rate, commitments, and visual budget projections)\n4. 🧠 **Financial Memory & Profile**: *'Remember that my grocery budget is ₹8,000 per month'* or *'What do you remember about my finances?'*\n5. 📅 **Future Planning & Commitments**: *'Plan ₹4500 for Bike Insurance on Dec 15'*\n6. 📊 **Interactive Visual Analytics**: *'Show pie chart of expenses'* or *'Show bar chart of commitments'*",
      chart: null,
      suggestions: [
        {
          question: "What do you remember about my finances?",
          tooltip: "Inspect remembered financial profile, budgets & preferences"
        },
        {
          question: "Remember that my grocery budget is ₹8,000 per month",
          tooltip: "Store a permanent budget constraint in your cloud ledger"
        },
        {
          question: "Predict my next month expenses",
          tooltip: "AI forecast based on recurring run-rate, variable spend & scheduled commitments"
        },
        {
          question: "Calculate today dairy amount",
          tooltip: "Queries only Dairy records from your ledger without hallucination"
        },
        {
          question: "Show pie chart of my expenses",
          tooltip: "Renders on-demand interactive visualization (Pie, Bar, Line)"
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
    memories_count: 0
  });
  const chatBottomRef = useRef(null);

  // Fetch summary stats
  const refreshStats = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/summary`);
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

  const handleSendMessage = async (textToSend) => {
    const message = textToSend || input;
    if (!message || !message.trim() || loading) return;

    const newMessages = [...messages, { role: 'user', text: message }];
    setMessages(newMessages);
    setInput('');
    setLoading(true);

    try {
      const historyPayload = newMessages.slice(-6).map(m => ({
        role: m.role,
        text: m.text
      }));

      const res = await fetch(`${API_BASE}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message, history: historyPayload })
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
          text: `⚠️ **Unable to connect to service**: ${err.message}.\n\nPlease ensure the backend API service is running.`,
          chart: null,
          suggestions: [
            { question: "Calculate today dairy amount", tooltip: "Retry querying dairy items" }
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

  // Interactive Quick Action Category Chips
  const quickActions = [
    { label: "🧠 Profile & Memories", query: "What do you remember about my finances?", tip: "View remembered financial profile & budgets" },
    { label: "🎯 Set Grocery Budget", query: "Remember that my grocery budget is ₹8000 per month", tip: "Store monthly grocery budget" },
    { label: "🔮 Predict Next Month", query: "Predict my next month expenses", tip: "Forecast future spending & run-rate" },
    { label: "🥛 Dairy", query: "Calculate today dairy amount", tip: "Query Dairy total" },
    { label: "🥦 Groceries", query: "How much spent on vegetables and groceries today?", tip: "Query Groceries total" },
    { label: "🍔 Food & Dining", query: "How much did I spend on food today?", tip: "Query Dining total" },
    { label: "🚗 Transport", query: "How much spent on transport today?", tip: "Query Transport total" },
    { label: "🏦 Loans & Bills", query: "How much spent on loans and bills?", tip: "Query Loans and Bills" },
    { label: "📅 Future", query: "Show future planned expenses", tip: "View upcoming commitments" },
    { label: "📊 Analytics", query: "Show pie chart of my expenses", tip: "Render dynamic visual chart" }
  ];

  return (
    <div className="flex h-screen w-full bg-linear-to-br from-slate-100 via-slate-50 to-indigo-50/30 text-slate-800 flex-col items-center justify-center p-0 sm:p-4">
      {/* 100% Chat Window Container */}
      <div className="w-full max-w-4xl h-full sm:h-[96vh] flex flex-col bg-white sm:border sm:border-slate-200/90 sm:rounded-3xl shadow-2xl overflow-hidden backdrop-blur-md">
        
        {/* Modern Executive Top Bar */}
        <header className="px-5 py-3.5 border-b border-slate-200/80 bg-white/95 backdrop-blur-sm flex flex-wrap items-center justify-between gap-3 shrink-0 shadow-xs">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-linear-to-tr from-indigo-600 via-indigo-500 to-violet-500 flex items-center justify-center shadow-md shadow-indigo-200/60 ring-2 ring-indigo-50">
              <Bot className="w-5 h-5 text-white" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-base font-bold text-slate-900 tracking-tight">Expense Copilot</h1>
                <span className="flex items-center gap-1.5 text-[11px] bg-emerald-50 text-emerald-700 px-2.5 py-0.5 rounded-full border border-emerald-200 font-semibold shadow-2xs">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
                  Live Cloud Sync
                </span>
              </div>
              <p className="text-[11px] text-slate-500 font-medium">Autonomous Financial Agent • Verified Real-time Ledger</p>
            </div>
          </div>

          {/* Live Dynamic Financial Metric Pills */}
          <div className="flex items-center gap-2.5">
            <div className="flex items-center gap-3 bg-linear-to-r from-slate-50 to-indigo-50/40 px-3.5 py-1.5 rounded-2xl border border-slate-200/80 text-xs shadow-2xs">
              <div className="flex items-center gap-1.5">
                <Wallet className="w-3.5 h-3.5 text-indigo-600" />
                <span className="text-slate-500 text-[11px]">Today:</span>
                <strong className="text-indigo-700 font-bold">
                  ₹{stats.today_total.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </strong>
              </div>
              <span className="text-slate-300">|</span>
              <div className="flex items-center gap-1.5">
                <Calendar className="w-3.5 h-3.5 text-emerald-600" />
                <span className="text-slate-500 text-[11px]">Planned:</span>
                <strong className="text-emerald-700 font-bold">
                  ₹{stats.future_total.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </strong>
              </div>
              <span className="text-slate-300">|</span>
              <button
                type="button"
                onClick={() => handleSendMessage("What do you remember about my finances?")}
                title="Click to view remembered financial profile & active memories"
                className="flex items-center gap-1.5 hover:opacity-80 transition-opacity cursor-pointer"
              >
                <Brain className="w-3.5 h-3.5 text-purple-600" />
                <span className="text-slate-500 text-[11px]">Memories:</span>
                <strong className="text-purple-700 font-bold">
                  {stats.memories_count || 0}
                </strong>
              </button>
            </div>
          </div>
        </header>

        {/* Message Stream */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-5 bg-linear-to-b from-slate-50/60 via-white to-slate-50/30">
          {messages.map((msg, index) => {
            const isUser = msg.role === 'user';
            return (
              <div
                key={index}
                className={`flex gap-3 ${isUser ? 'justify-end' : 'justify-start'}`}
              >
                {!isUser && (
                  <div className="w-8 h-8 rounded-xl bg-linear-to-tr from-indigo-600 to-violet-600 flex items-center justify-center shrink-0 mt-1 shadow-sm shadow-indigo-100">
                    <Bot className="w-4 h-4 text-white" />
                  </div>
                )}

                <div
                  className={`max-w-[92%] sm:max-w-[82%] rounded-2xl p-4 text-sm leading-relaxed transition-all ${
                    isUser
                      ? 'bg-linear-to-r from-indigo-600 to-indigo-700 text-white rounded-br-xs shadow-md shadow-indigo-200/50'
                      : 'bg-white text-slate-800 border border-slate-200/80 rounded-tl-xs shadow-sm hover:border-slate-300'
                  }`}
                >
                  <div className="space-y-1">{renderFormattedText(msg.text)}</div>

                  {/* Dynamic Recharts Visualization with Live Tab Switcher */}
                  {msg.chart && <DynamicChart chart={msg.chart} />}

                  {/* Suggestion Prompts with Radix Tooltips */}
                  {msg.suggestions && msg.suggestions.length > 0 && (
                    <div className="mt-3.5 pt-3 border-t border-slate-100">
                      <div className="flex items-center gap-1.5 text-[11px] text-slate-500 mb-2 font-medium">
                        <ArrowDownCircle className="w-3.5 h-3.5 text-indigo-600" />
                        <span>Interactive Prompts (Click or Hover for Insights):</span>
                      </div>
                      <TooltipPicker
                        suggestions={msg.suggestions}
                        onSelect={(question) => handleSendMessage(question)}
                      />
                    </div>
                  )}
                </div>

                {isUser && (
                  <div className="w-8 h-8 rounded-xl bg-linear-to-tr from-slate-200 to-slate-300 flex items-center justify-center shrink-0 mt-1 shadow-xs">
                    <User className="w-4 h-4 text-slate-700" />
                  </div>
                )}
              </div>
            );
          })}

          {loading && (
            <div className="flex gap-3 justify-start items-center text-slate-500 text-xs py-2 px-1">
              <div className="w-8 h-8 rounded-xl bg-indigo-50 border border-indigo-200 flex items-center justify-center shadow-xs">
                <Loader2 className="w-4 h-4 text-indigo-600 animate-spin" />
              </div>
              <span className="font-medium text-indigo-600/90 animate-pulse">Analyzing ledger and computing results...</span>
            </div>
          )}

          <div ref={chatBottomRef} />
        </div>

        {/* Interactive Quick-Filter Category Bar */}
        <div className="px-4 py-2.5 bg-slate-50/90 border-t border-slate-200/70 flex items-center gap-2 overflow-x-auto scrollbar-none">
          <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider shrink-0 flex items-center gap-1">
            ⚡ Quick Actions:
          </span>
          {quickActions.map((qa, i) => (
            <button
              key={i}
              type="button"
              onClick={() => handleSendMessage(qa.query)}
              title={qa.tip}
              className="shrink-0 px-3 py-1.5 rounded-full text-xs font-semibold bg-white hover:bg-indigo-600 text-slate-700 hover:text-white border border-slate-200/80 hover:border-indigo-600 shadow-2xs hover:shadow-sm transition-all duration-200 cursor-pointer active:scale-95"
            >
              {qa.label}
            </button>
          ))}
        </div>

        {/* Modern Interactive Input Bar */}
        <div className="p-3 sm:p-4 bg-white border-t border-slate-200 shrink-0">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSendMessage();
            }}
            className="flex items-center gap-2.5"
          >
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="e.g. 'Milk 45, Vegetables 120' or 'Calculate today dairy amount'..."
              className="flex-1 bg-slate-50/80 border border-slate-200 text-slate-900 rounded-2xl px-4 py-3 text-sm focus:outline-none focus:border-indigo-600 focus:bg-white focus:ring-2 focus:ring-indigo-100 transition-all placeholder:text-slate-400 font-normal"
            />
            <button
              type="submit"
              disabled={loading || !input.trim()}
              className="bg-linear-to-r from-indigo-600 to-violet-600 hover:from-indigo-700 hover:to-violet-700 disabled:opacity-40 disabled:cursor-not-allowed text-white font-medium px-4.5 py-3 rounded-2xl transition-all duration-200 flex items-center justify-center shadow-md shadow-indigo-200/50 cursor-pointer active:scale-95"
            >
              <Send className="w-4 h-4" />
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
