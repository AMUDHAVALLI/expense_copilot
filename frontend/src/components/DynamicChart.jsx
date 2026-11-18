import React, { useState } from 'react';
import {
  BarChart, Bar, PieChart, Pie, Cell, LineChart, Line,
  XAxis, YAxis, Tooltip, ResponsiveContainer, Legend
} from 'recharts';
import { PieChart as PieIcon, BarChart3 as BarIcon, TrendingUp as LineIcon } from 'lucide-react';

const PALETTE = [
  '#4F46E5', // Indigo
  '#059669', // Emerald
  '#D97706', // Amber
  '#DC2626', // Red
  '#7C3AED', // Violet
  '#0284C7', // Sky Blue
  '#DB2777', // Pink
  '#475569', // Slate
];

export default function DynamicChart({ chart }) {
  if (!chart || !chart.data || chart.data.length === 0) {
    return null;
  }

  // Allow user to interactively switch chart type on the fly
  const [activeType, setActiveType] = useState((chart.type || 'pie').toLowerCase());

  return (
    <div className="mt-3 p-4 bg-white rounded-xl border border-slate-200/90 text-slate-800 shadow-sm transition-all">
      {/* Chart Header & Interactive Switcher */}
      <div className="flex flex-wrap items-center justify-between gap-2 mb-3 border-b border-slate-100 pb-2.5">
        <span className="text-xs font-bold text-slate-800 tracking-wide flex items-center gap-1.5">
          <span>📊</span> {chart.title || 'Expense Breakdown'}
        </span>

        {/* Interactive Chart Type Toggle */}
        <div className="flex items-center gap-1 bg-slate-100 p-0.5 rounded-lg border border-slate-200">
          <button
            type="button"
            onClick={() => setActiveType('pie')}
            className={`flex items-center gap-1 px-2 py-1 rounded text-[11px] font-medium transition-all ${
              activeType === 'pie'
                ? 'bg-white text-indigo-600 shadow-xs'
                : 'text-slate-500 hover:text-slate-800'
            }`}
            title="Switch to Pie Chart"
          >
            <PieIcon className="w-3 h-3" />
            <span>Pie</span>
          </button>
          <button
            type="button"
            onClick={() => setActiveType('bar')}
            className={`flex items-center gap-1 px-2 py-1 rounded text-[11px] font-medium transition-all ${
              activeType === 'bar'
                ? 'bg-white text-indigo-600 shadow-xs'
                : 'text-slate-500 hover:text-slate-800'
            }`}
            title="Switch to Bar Chart"
          >
            <BarIcon className="w-3 h-3" />
            <span>Bar</span>
          </button>
          <button
            type="button"
            onClick={() => setActiveType('line')}
            className={`flex items-center gap-1 px-2 py-1 rounded text-[11px] font-medium transition-all ${
              activeType === 'line'
                ? 'bg-white text-indigo-600 shadow-xs'
                : 'text-slate-500 hover:text-slate-800'
            }`}
            title="Switch to Line Trend"
          >
            <LineIcon className="w-3 h-3" />
            <span>Trend</span>
          </button>
        </div>
      </div>

      {/* Chart Canvas */}
      <div className="w-full h-56">
        <ResponsiveContainer width="100%" height="100%">
          {activeType === 'pie' ? (
            <PieChart>
              <Pie
                data={chart.data}
                cx="50%"
                cy="50%"
                innerRadius={48}
                outerRadius={75}
                paddingAngle={4}
                dataKey="value"
                nameKey="name"
                animationDuration={600}
              >
                {chart.data.map((_, index) => (
                  <Cell 
                    key={`cell-${index}`} 
                    fill={PALETTE[index % PALETTE.length]} 
                    stroke="#ffffff" 
                    strokeWidth={2} 
                  />
                ))}
              </Pie>
              <Tooltip
                formatter={(val) => [`₹${val}`, 'Amount']}
                contentStyle={{
                  backgroundColor: '#ffffff',
                  borderColor: '#e2e8f0',
                  borderRadius: '8px',
                  color: '#0f172a',
                  fontSize: '12px',
                  boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)'
                }}
              />
              <Legend
                verticalAlign="bottom"
                height={28}
                iconType="circle"
                wrapperStyle={{ fontSize: '11px', color: '#475569' }}
              />
            </PieChart>
          ) : activeType === 'line' ? (
            <LineChart data={chart.data} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
              <XAxis dataKey="name" stroke="#94A3B8" fontSize={11} tickLine={false} />
              <YAxis stroke="#94A3B8" fontSize={11} tickLine={false} />
              <Tooltip
                formatter={(val) => [`₹${val}`, 'Amount']}
                contentStyle={{
                  backgroundColor: '#ffffff',
                  borderColor: '#e2e8f0',
                  borderRadius: '8px',
                  color: '#0f172a',
                  fontSize: '12px',
                  boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)'
                }}
              />
              <Line
                type="monotone"
                dataKey="value"
                stroke="#4F46E5"
                strokeWidth={3}
                dot={{ r: 5, fill: '#6366F1' }}
                activeDot={{ r: 7 }}
                animationDuration={600}
              />
            </LineChart>
          ) : (
            <BarChart data={chart.data} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
              <XAxis dataKey="name" stroke="#94A3B8" fontSize={11} tickLine={false} />
              <YAxis stroke="#94A3B8" fontSize={11} tickLine={false} />
              <Tooltip
                formatter={(val) => [`₹${val}`, 'Amount']}
                contentStyle={{
                  backgroundColor: '#ffffff',
                  borderColor: '#e2e8f0',
                  borderRadius: '8px',
                  color: '#0f172a',
                  fontSize: '12px',
                  boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)'
                }}
              />
              <Bar dataKey="value" radius={[5, 5, 0, 0]} animationDuration={600}>
                {chart.data.map((_, index) => (
                  <Cell key={`cell-${index}`} fill={PALETTE[index % PALETTE.length]} />
                ))}
              </Bar>
            </BarChart>
          )}
        </ResponsiveContainer>
      </div>
    </div>
  );
}
