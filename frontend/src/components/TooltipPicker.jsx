import React, { useState } from 'react';
import { HelpCircle, Sparkles } from 'lucide-react';

export default function TooltipPicker({ suggestions, onSelect }) {
  if (!suggestions || suggestions.length === 0) return null;

  return (
    <div className="flex flex-wrap gap-2 pt-2">
      {suggestions.map((item, idx) => {
        const questionText = typeof item === 'string' ? item : item.question;
        const tooltipText = typeof item === 'string' 
          ? `Click to ask: "${item}"` 
          : (item.tooltip || `Click to ask: "${item.question}"`);

        return (
          <TooltipButton 
            key={idx} 
            question={questionText} 
            tooltip={tooltipText} 
            onClick={() => onSelect(questionText)} 
          />
        );
      })}
    </div>
  );
}

function TooltipButton({ question, tooltip, onClick }) {
  const [hovered, setHovered] = useState(false);

  return (
    <div className="relative inline-block">
      <button
        type="button"
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}
        onClick={onClick}
        className="group flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium 
                   bg-white hover:bg-indigo-50/90 text-indigo-700 hover:text-indigo-900 
                   border border-slate-200/90 hover:border-indigo-300 transition-all duration-150 
                   shadow-xs cursor-pointer active:scale-95 text-left"
      >
        <Sparkles className="w-3 h-3 text-indigo-400 group-hover:text-indigo-600 shrink-0" />
        <span>{question}</span>
        <HelpCircle className="w-3.5 h-3.5 text-slate-300 group-hover:text-indigo-600 shrink-0 transition-colors ml-0.5" />
      </button>

      {/* Floating Tooltip Bubble */}
      {hovered && (
        <div className="absolute bottom-full left-4 mb-2 z-50 pointer-events-none transition-all duration-150 animate-in fade-in zoom-in-95">
          <div className="bg-slate-900 text-white text-[11px] px-3 py-1.5 rounded-lg shadow-xl whitespace-nowrap flex items-center gap-1.5 border border-slate-700">
            <span className="text-amber-400 font-bold">💡</span>
            <span>{tooltip}</span>
          </div>
          <div className="w-2 h-2 bg-slate-900 border-r border-b border-slate-700 rotate-45 ml-4 -mt-1" />
        </div>
      )}
    </div>
  );
}
