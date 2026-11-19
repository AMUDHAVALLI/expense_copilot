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
      text: "👋 **Welcome to Expense Copilot!**\n\nI am your autonomous financial assistant. Here is what I can do for you:\n\n1. 🛒 **Track Expenses**: *'Milk 45, Vegetables 120 and Bread 35'*\n2. 🔍 **Precise Category Calculations**: *'Calculate today dairy amount'* (Strictly filters and sums Dairy items without hallucination)\n3. 🔮 **Predictive Forecasting**: *'Predict my next month expenses'* (Forecasts monthly burn-rate, commitments, and visual budget projections)\n4. 🧠 **Financial Memory & Profile**: *'Remember that my grocery budget is ₹8,000 per month'* or *'What do you remember about my finances?'*\n5. 📅 **Future Planning & Commitments**: *'Plan ₹4500 for Bike Insurance on Dec 15'*\n6. 📊 **Interactive Visual Analytics**: *'Show pie chart of expenses'* or *'Show bar chart of commitments'*",
      chart: null,
      suggestions: [
        {
          question: "What do you remember about my finances?",
          tooltip: "Inspect remembered financial profile, budgets & preferences"
        },
        {
          question: "Remember that my grocery budget is ₹8,000 per month",
          tooltip: "Store a permanent budget constraint in your ledger"
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
        <p key={idx} className={line.trim() === '' ? 'h-2' : 'my-0.5 leading-relaxed'}>
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
    { label: "🔮 Predict Month", query: "Predict my next month expenses", tip: "Forecast future spending & run-rate", highlight: "indigo" },
    { label: "🧠 Financial Profile", query: "What do you remember about my finances?", tip: "View remembered financial profile & budgets", highlight: "purple" },
    { label: "🎯 Set Grocery Budget", query: "Remember that my grocery budget is ₹8000 per month", tip: "Store monthly grocery budget", highlight: "emerald" },
    { label: "🥛 Dairy", query: "Calculate today dairy amount", tip: "Query Dairy total" },
    { label: "🥦 Groceries", query: "How much spent on vegetables and groceries today?", tip: "Query Groceries total" },
    { label: "🍔 Dining", query: "How much did I spend on food today?", tip: "Query Dining total" },
    { label: "🚗 Transport", query: "How much spent on transport today?", tip: "Query Transport total" },
    { label: "🏦 Loans & EMI", query: "How much spent on loans and bills?", tip: "Query Loans and Bills" },
    { label: "📅 Commitments", query: "Show future planned expenses", tip: "View upcoming commitments" },
    { label: "📊 Analytics", query: "Show pie chart of my expenses", tip: "Render dynamic visual chart" }
  ];

  return (
    <div className="flex h-screen w-full bg-slate-100/90 text-slate-800 flex-col items-center justify-center p-0 sm:p-4 selection:bg-indigo-500 selection:text-white">
      {/* Executive Financial Dashboard Window */}
      <div className="w-full max-w-4xl h-full sm:h-[96vh] flex flex-col bg-white sm:border sm:border-slate-200/90 sm:rounded-3xl shadow-[0_20px_60px_-15px_rgba(79,70,229,0.08)] overflow-hidden">
        
        {/* Modern Executive Top Bar */}
        <header className="px-5 py-3.5 border-b border-slate-200/80 bg-white/95 backdrop-blur-md flex flex-wrap items-center justify-between gap-3 shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-linear-to-tr from-indigo-600 via-indigo-500 to-violet-600 flex items-center justify-center shadow-md shadow-indigo-300/40 ring-4 ring-indigo-50">
              <Sparkles className="w-5 h-5 text-white" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-base font-bold text-slate-900 tracking-tight">Expense Copilot</h1>
                <span className="px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-indigo-50 text-indigo-700 border border-indigo-200/60">
                  AI Intelligence
                </span>
              </div>
              <p className="text-[11px] text-slate-500 font-medium">Autonomous Financial Agent • Predictive Analytics & Memory</p>
            </div>
          </div>

          {/* Interactive Financial Metric Badges */}
          <div className="flex items-center gap-2">
            {/* Today's Spend Chip */}
            <div className="flex items-center gap-2 bg-indigo-50/70 hover:bg-indigo-50 border border-indigo-100/80 px-3 py-1.5 rounded-2xl text-xs transition-all shadow-2xs">
              <div className="w-6 h-6 rounded-lg bg-indigo-600/10 flex items-center justify-center">
                <Wallet className="w-3.5 h-3.5 text-indigo-600" />
              </div>
              <div className="flex flex-col leading-tight">
                <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">Today</span>
                <strong className="text-indigo-900 font-bold">
                  ₹{stats.today_total.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </strong>
              </div>
            </div>

            {/* Planned Commitments Chip */}
            <div className="flex items-center gap-2 bg-emerald-50/70 hover:bg-emerald-50 border border-emerald-100/80 px-3 py-1.5 rounded-2xl text-xs transition-all shadow-2xs">
              <div className="w-6 h-6 rounded-lg bg-emerald-600/10 flex items-center justify-center">
                <Calendar className="w-3.5 h-3.5 text-emerald-600" />
              </div>
              <div className="flex flex-col leading-tight">
                <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">Planned</span>
                <strong className="text-emerald-900 font-bold">
                  ₹{stats.future_total.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </strong>
              </div>
            </div>

            {/* Financial Memory Chip */}
            <button
              type="button"
              onClick={() => handleSendMessage("What do you remember about my finances?")}
              title="Click to view remembered financial profile & active memories"
              className="flex items-center gap-2 bg-purple-50/70 hover:bg-purple-100/80 border border-purple-100/80 px-3 py-1.5 rounded-2xl text-xs transition-all shadow-2xs cursor-pointer active:scale-95"
            >
              <div className="w-6 h-6 rounded-lg bg-purple-600/10 flex items-center justify-center">
                <Brain className="w-3.5 h-3.5 text-purple-600" />
              </div>
              <div className="flex flex-col leading-tight text-left">
                <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">Memories</span>
                <strong className="text-purple-900 font-bold">
                  {stats.memories_count || 0} Saved
                </strong>
              </div>
            </button>
          </div>
        </header>

        {/* Message Stream */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-5 bg-linear-to-b from-slate-50/50 via-white to-slate-50/20">
          {messages.map((msg, index) => {
            const isUser = msg.role === 'user';
            return (
              <div
                key={index}
                className={`flex gap-3.5 ${isUser ? 'justify-end' : 'justify-start'}`}
              >
                {!isUser && (
                  <div className="w-9 h-9 rounded-2xl bg-linear-to-tr from-indigo-600 via-indigo-500 to-violet-600 flex items-center justify-center shrink-0 mt-1 shadow-sm shadow-indigo-200">
                    <Sparkles className="w-4 h-4 text-white" />
                  </div>
                )}

                <div
                  className={`max-w-[92%] sm:max-w-[82%] rounded-3xl p-4.5 sm:p-5 text-sm leading-relaxed transition-all duration-200 ${
                    isUser
                      ? 'bg-linear-to-r from-indigo-600 to-violet-600 text-white rounded-br-xs shadow-md shadow-indigo-300/30'
                      : 'bg-white text-slate-800 border border-slate-200/80 rounded-tl-xs shadow-[0_2px_12px_rgba(0,0,0,0.03)] hover:border-slate-300/80'
                  }`}
                >
                  <div className="space-y-1.5">{renderFormattedText(msg.text)}</div>

                  {/* Dynamic Recharts Visualization with Live Tab Switcher */}
                  {msg.chart && <DynamicChart chart={msg.chart} />}

                  {/* Suggestion Prompts with Radix Tooltips */}
                  {msg.suggestions && msg.suggestions.length > 0 && (
                    <div className="mt-4 pt-3.5 border-t border-slate-100">
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
                  <div className="w-9 h-9 rounded-2xl bg-linear-to-tr from-slate-200 to-slate-300 flex items-center justify-center shrink-0 mt-1 shadow-xs border border-slate-300/60">
                    <User className="w-4 h-4 text-slate-700" />
                  </div>
                )}
              </div>
            );
          })}

          {loading && (
            <div className="flex gap-3 justify-start items-center text-slate-500 text-xs py-2 px-1">
              <div className="w-9 h-9 rounded-2xl bg-indigo-50 border border-indigo-200 flex items-center justify-center shadow-xs">
                <Loader2 className="w-4.5 h-4.5 text-indigo-600 animate-spin" />
              </div>
              <div className="flex items-center gap-2">
                <span className="font-semibold text-indigo-600 animate-pulse">Analyzing ledger & synthesizing response...</span>
              </div>
            </div>
          )}

          <div ref={chatBottomRef} />
        </div>

        {/* Interactive Quick-Action Category Bar */}
        <div className="px-4 py-2.5 bg-slate-50/90 border-t border-slate-200/70 flex items-center gap-2 overflow-x-auto scrollbar-none">
          <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider shrink-0 flex items-center gap-1 mr-1">
            ⚡ Quick Actions:
          </span>
          {quickActions.map((qa, i) => (
            <button
              key={i}
              type="button"
              onClick={() => handleSendMessage(qa.query)}
              title={qa.tip}
              className={`shrink-0 px-3 py-1.5 rounded-full text-xs font-semibold shadow-2xs hover:shadow-sm transition-all duration-200 cursor-pointer active:scale-95 ${
                qa.highlight === 'indigo'
                  ? 'bg-indigo-50 hover:bg-indigo-600 text-indigo-700 hover:text-white border border-indigo-200 hover:border-indigo-600'
                  : qa.highlight === 'purple'
                  ? 'bg-purple-50 hover:bg-purple-600 text-purple-700 hover:text-white border border-purple-200 hover:border-purple-600'
                  : qa.highlight === 'emerald'
                  ? 'bg-emerald-50 hover:bg-emerald-600 text-emerald-700 hover:text-white border border-emerald-200 hover:border-emerald-600'
                  : 'bg-white hover:bg-indigo-600 text-slate-700 hover:text-white border border-slate-200/80 hover:border-indigo-600'
              }`}
            >
              {qa.label}
            </button>
          ))}
        </div>

        {/* Modern Interactive Command Input Bar */}
        <div className="p-3.5 sm:p-4 bg-white border-t border-slate-200 shrink-0">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSendMessage();
            }}
            className="flex items-center gap-2.5"
          >
            <div className="flex-1 flex items-center bg-slate-50 border border-slate-200 rounded-2xl px-4 py-1.5 focus-within:bg-white focus-within:border-indigo-600 focus-within:ring-3 focus-within:ring-indigo-100 transition-all duration-200">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask e.g. 'Predict my next month expenses' or 'Milk 45, Vegetables 120'..."
                className="flex-1 bg-transparent border-none text-slate-900 py-2 text-sm focus:outline-none placeholder:text-slate-400 font-normal"
              />
              <kbd className="hidden sm:inline-flex items-center px-2 py-0.5 text-[10px] font-semibold text-slate-400 bg-slate-100 rounded-md border border-slate-200 shrink-0 select-none">
                Enter ↵
              </kbd>
            </div>
            <button
              type="submit"
              disabled={loading || !input.trim()}
              className="bg-linear-to-r from-indigo-600 to-violet-600 hover:from-indigo-700 hover:to-violet-700 disabled:opacity-40 disabled:cursor-not-allowed text-white font-semibold px-5 py-3 rounded-2xl transition-all duration-200 flex items-center justify-center shadow-md shadow-indigo-300/40 hover:shadow-lg hover:shadow-indigo-300/50 hover:-translate-y-0.5 active:translate-y-0 cursor-pointer"
            >
              <Send className="w-4 h-4" />
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
