"""Flask web application."""

from __future__ import annotations

import sqlite3
import threading
from datetime import timedelta
from typing import Any, Dict, List, Optional, Tuple

from flask import Flask, Response, g, redirect, render_template_string, request, url_for

from . import db, ingest, rules, utils

TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>{{ title }}</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0"></script>
  <style>
    :root {
      /* Modern Color Palette */
      --bg-primary: #0a0a0a;
      --bg-secondary: #111111;
      --bg-tertiary: #1a1a1a;
      --bg-card: linear-gradient(135deg, #1a1a1a 0%, #0f0f0f 100%);
      --bg-card-hover: linear-gradient(135deg, #202020 0%, #141414 100%);

      --border-primary: #2a2a2a;
      --border-secondary: #333333;
      --border-accent: #3b82f6;

      --text-primary: #f8fafc;
      --text-secondary: #cbd5e1;
      --text-muted: #94a3b8;

      --accent-blue: #3b82f6;
      --accent-blue-hover: #2563eb;
      --accent-green: #10b981;
      --accent-red: #ef4444;
      --accent-orange: #f59e0b;

      /* Shadows */
      --shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.25);
      --shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.3), 0 2px 4px -2px rgb(0 0 0 / 0.3);
      --shadow-lg: 0 10px 15px -3px rgb(0 0 0 / 0.4), 0 4px 6px -4px rgb(0 0 0 / 0.4);

      /* Typography */
      --font-mono: ui-monospace, SFMono-Regular, "SF Mono", Monaco, Consolas, "Liberation Mono", "Courier New", monospace;

      /* Animations */
      --transition-fast: 150ms cubic-bezier(0.4, 0, 0.2, 1);
      --transition-normal: 250ms cubic-bezier(0.4, 0, 0.2, 1);
      --transition-slow: 350ms cubic-bezier(0.4, 0, 0.2, 1);
    }

    /* Modern scrollbar */
    ::-webkit-scrollbar {
      width: 8px;
      height: 8px;
    }

    ::-webkit-scrollbar-track {
      background: var(--bg-secondary);
    }

    ::-webkit-scrollbar-thumb {
      background: var(--border-primary);
      border-radius: 4px;
    }

    ::-webkit-scrollbar-thumb:hover {
      background: var(--border-secondary);
    }

    /* Mobile-first responsive improvements */
    @media (max-width: 768px) {
      .modern-card {
        border-radius: 12px;
        padding: 1rem;
      }

      .modern-card:hover {
        transform: none; /* Disable hover transforms on mobile */
      }

      .modern-table {
        font-size: 12px;
      }

      .modern-table th,
      .modern-table td {
        padding: 8px 12px;
      }

      /* Stack filter controls vertically on mobile */
      .filter-controls {
        flex-direction: column;
        gap: 1rem;
      }

      .filter-controls .modern-select,
      .filter-controls .modern-input {
        width: 100%;
      }

      /* Improve badge layout on mobile */
      .badge {
        font-size: 10px;
        padding: 3px 6px;
      }

      /* Better spacing for news items on mobile */
      .news-item-mobile {
        padding: 1rem;
        margin-bottom: 0.5rem;
        border-radius: 8px;
      }
    }

    @media (max-width: 640px) {
      /* Hide less critical information on very small screens */
      .mobile-hidden {
        display: none;
      }

      /* Simplify header on mobile */
      .mobile-header-simplified h1 {
        font-size: 1.5rem;
      }

      .mobile-header-simplified .filter-controls {
        flex-direction: column;
        gap: 0.5rem;
      }

      /* Stack grid items vertically on mobile */
      .mobile-grid-stack {
        grid-template-columns: 1fr;
      }
    }

    /* Loading skeleton enhancements */
    .skeleton-card {
      background: var(--bg-card);
      border: 1px solid var(--border-primary);
      border-radius: 16px;
      padding: 1.5rem;
      animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
    }

    .skeleton-text {
      background: var(--bg-tertiary);
      border-radius: 4px;
      height: 1rem;
      margin-bottom: 0.5rem;
    }

    .skeleton-text:last-child {
      margin-bottom: 0;
      width: 60%;
    }

    .skeleton-chart {
      background: var(--bg-tertiary);
      border-radius: 8px;
      height: 120px;
      animation: loading 1.5s infinite;
    }

    /* Enhanced focus states for accessibility */
    .focus-ring:focus {
      outline: none;
      box-shadow: 0 0 0 3px rgb(59 130 246 / 0.5);
    }

    /* Improved button loading states */
    .btn-loading {
      opacity: 0.7;
      cursor: not-allowed;
    }

    .btn-loading::after {
      content: "";
      display: inline-block;
      width: 1rem;
      height: 1rem;
      border: 2px solid transparent;
      border-top: 2px solid currentColor;
      border-radius: 50%;
      animation: spin 1s linear infinite;
      margin-left: 0.5rem;
    }

    @keyframes spin {
      to { transform: rotate(360deg); }
    }

    /* Loading animation */
    @keyframes pulse {
      0%, 100% { opacity: 1; }
      50% { opacity: 0.5; }
    }

    .animate-pulse {
      animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
    }

    /* Fade in animation */
    @keyframes fadeIn {
      from { opacity: 0; transform: translateY(10px); }
      to { opacity: 1; transform: translateY(0); }
    }

    .animate-fade-in {
      animation: fadeIn 0.5s ease-out;
    }

    /* Modern card styles */
    .modern-card {
      background: var(--bg-card);
      border: 1px solid var(--border-primary);
      border-radius: 16px;
      box-shadow: var(--shadow-sm);
      transition: all var(--transition-normal);
    }

    .modern-card:hover {
      background: var(--bg-card-hover);
      border-color: var(--border-secondary);
      box-shadow: var(--shadow-md);
      transform: translateY(-2px);
    }

    /* Modern button styles */
    .btn-primary {
      background: linear-gradient(135deg, var(--accent-blue) 0%, var(--accent-blue-hover) 100%);
      border: none;
      border-radius: 12px;
      color: white;
      font-weight: 500;
      padding: 8px 16px;
      transition: all var(--transition-fast);
      box-shadow: var(--shadow-sm);
    }

    .btn-primary:hover {
      transform: translateY(-1px);
      box-shadow: var(--shadow-md);
    }

    .btn-secondary {
      background: var(--bg-tertiary);
      border: 1px solid var(--border-primary);
      border-radius: 12px;
      color: var(--text-secondary);
      font-weight: 500;
      padding: 8px 16px;
      transition: all var(--transition-fast);
    }

    .btn-secondary:hover {
      background: var(--bg-secondary);
      border-color: var(--border-secondary);
      color: var(--text-primary);
    }

    /* Modern form styles */
    .modern-select, .modern-input {
      background: var(--bg-secondary);
      border: 1px solid var(--border-primary);
      border-radius: 12px;
      color: var(--text-primary);
      padding: 8px 12px;
      transition: all var(--transition-fast);
      font-size: 14px;
    }

    .modern-select:focus, .modern-input:focus {
      outline: none;
      border-color: var(--accent-blue);
      box-shadow: 0 0 0 3px rgb(59 130 246 / 0.1);
    }

    /* Modern table styles */
    .modern-table {
      width: 100%;
      border-collapse: separate;
      border-spacing: 0;
    }

    .modern-table th {
      background: var(--bg-tertiary);
      color: var(--text-secondary);
      font-weight: 600;
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      padding: 12px 16px;
      text-align: left;
      border-bottom: 1px solid var(--border-primary);
    }

    .modern-table td {
      padding: 12px 16px;
      border-bottom: 1px solid var(--border-primary);
      transition: background-color var(--transition-fast);
    }

    .modern-table tbody tr:hover td {
      background: rgba(59, 130, 246, 0.05);
    }

    .modern-table tbody tr:nth-child(even) td {
      background: rgba(255, 255, 255, 0.01);
    }

    /* Status badges */
    .badge {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 4px 8px;
      border-radius: 8px;
      font-size: 11px;
      font-weight: 500;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }

    .badge-positive { background: rgba(16, 185, 129, 0.1); color: var(--accent-green); border: 1px solid rgba(16, 185, 129, 0.2); }
    .badge-negative { background: rgba(239, 68, 68, 0.1); color: var(--accent-red); border: 1px solid rgba(239, 68, 68, 0.2); }
    .badge-neutral { background: rgba(148, 163, 184, 0.1); color: var(--text-muted); border: 1px solid rgba(148, 163, 184, 0.2); }
    .badge-mixed { background: rgba(245, 158, 11, 0.1); color: var(--accent-orange); border: 1px solid rgba(245, 158, 11, 0.2); }

    .badge-asset { background: rgba(16, 185, 129, 0.1); color: var(--accent-green); border: 1px solid rgba(16, 185, 129, 0.2); }
    .badge-geo { background: rgba(59, 130, 246, 0.1); color: #60a5fa; border: 1px solid rgba(59, 130, 246, 0.2); }

    /* Loading skeleton */
    .skeleton {
      background: linear-gradient(90deg, var(--bg-tertiary) 25%, var(--bg-secondary) 50%, var(--bg-tertiary) 75%);
      background-size: 200% 100%;
      animation: loading 1.5s infinite;
    }

    @keyframes loading {
      0% { background-position: 200% 0; }
      100% { background-position: -200% 0; }
    }
  </style>
</head>
<body class="bg-[var(--bg-primary)] text-[var(--text-primary)] animate-fade-in">
  <div class="max-w-7xl mx-auto p-4 md:p-8">
    <div class="flex flex-col md:flex-row md:items-end md:justify-between gap-4 animate-fade-in">
      <div>
        <h1 class="text-3xl md:text-4xl font-bold bg-gradient-to-r from-white to-slate-300 bg-clip-text text-transparent">{{ title }}</h1>
        <div class="text-[var(--text-secondary)] mt-2 text-sm flex items-center gap-4">
          <span class="flex items-center gap-2">
            <div class="w-2 h-2 bg-[var(--accent-blue)] rounded-full"></div>
            Lookback: <span class="font-semibold text-[var(--text-primary)]">{{ lookback_hours }}h</span>
          </span>
          {% if category %}
            <span class="flex items-center gap-2">
              <div class="w-2 h-2 bg-[var(--accent-green)] rounded-full"></div>
              Category: <span class="font-semibold text-[var(--text-primary)]">{{ category }}</span>
            </span>
          {% endif %}
          {% if topic %}
            <span class="flex items-center gap-2">
              <div class="w-2 h-2 bg-[var(--accent-orange)] rounded-full"></div>
              Topic: <span class="font-semibold text-[var(--text-primary)]">{{ topic }}</span>
            </span>
          {% endif %}
        </div>
      </div>
      <div class="flex flex-wrap gap-3 items-center">
        <a class="btn-secondary text-sm" href="{{ url_for('fetch_now') }}">
          <span class="flex items-center gap-2">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path>
            </svg>
            Fetch now
          </span>
        </a>
        <form method="get" class="flex flex-wrap gap-3 items-center">
          <select name="lookback" class="modern-select text-sm">
            {% for h in [6,12,24,48,72,168] %}
              <option value="{{h}}" {% if h==lookback_hours %}selected{% endif %}>{{h}}h</option>
            {% endfor %}
          </select>
          <select name="category" class="modern-select text-sm">
            <option value="">All categories</option>
            <option value="A" {% if "A"==category %}selected{% endif %}>📈 Market News</option>
            <option value="B" {% if "B"==category %}selected{% endif %}>📰 Interpretive/Opinion</option>
            <option value="C" {% if "C"==category %}selected{% endif %}>🏛️ Macro/Policy Anchors</option>
            <option value="D" {% if "D"==category %}selected{% endif %}>💼 Practitioner Commentary</option>
            <option value="E" {% if "E"==category %}selected{% endif %}>📊 Other</option>
          </select>
          <input name="topic" value="{{ topic or '' }}" placeholder="topic tag (e.g., rates)" class="modern-input text-sm w-56" />
          <button class="btn-primary text-sm font-medium" type="submit">
            <span class="flex items-center gap-2">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z"></path>
              </svg>
              Apply
            </span>
          </button>
          <a class="btn-secondary text-sm" href="{{ url_for('index') }}">
            <span class="flex items-center gap-2">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path>
              </svg>
              Reset
            </span>
          </a>
        </form>
      </div>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6 mt-8">
      <div class="modern-card p-6 animate-fade-in" style="animation-delay: 0.1s">
        <div class="flex items-center gap-3 mb-4">
          <div class="w-10 h-10 bg-gradient-to-br from-blue-500 to-blue-600 rounded-xl flex items-center justify-center">
            <svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path>
            </svg>
          </div>
          <div>
            <div class="text-lg font-semibold text-[var(--text-primary)]">Ingestion Status</div>
            <div class="text-sm text-[var(--text-muted)]">Real-time feed health</div>
          </div>
        </div>
        <div class="space-y-3">
          <div class="flex justify-between items-center">
            <span class="text-[var(--text-secondary)]">Last run (UTC):</span>
            <span class="font-mono text-sm bg-[var(--bg-tertiary)] px-2 py-1 rounded-lg">{{ status.last_run_utc or "—" }}</span>
          </div>
          <div class="flex justify-between items-center">
            <span class="text-[var(--text-secondary)]">Items added:</span>
            <span class="font-semibold text-[var(--accent-green)]">{{ status.items_added }}</span>
          </div>
          <div class="flex justify-between items-center">
            <span class="text-[var(--text-secondary)]">Last error:</span>
            <span class="font-medium {% if status.last_error %}text-[var(--accent-red)]{% else %}text-[var(--text-muted)]{% endif %}">{{ status.last_error or "none" }}</span>
          </div>
        </div>
      </div>

      <div class="modern-card p-6 lg:col-span-2 animate-fade-in" style="animation-delay: 0.2s">
        <div class="flex items-center justify-between mb-4">
          <div class="flex items-center gap-3">
            <div class="w-10 h-10 bg-gradient-to-br from-purple-500 to-purple-600 rounded-xl flex items-center justify-center">
              <svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a.997.997 0 01-1.414 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z"></path>
              </svg>
            </div>
            <div>
              <div class="text-lg font-semibold text-[var(--text-primary)]">Top Topics</div>
              <div class="text-sm text-[var(--text-muted)]">Trending conversation drivers</div>
            </div>
          </div>
          <div class="text-xs text-[var(--text-muted)] bg-[var(--bg-tertiary)] px-3 py-1 rounded-full">
            Deterministic tags v0
          </div>
        </div>
        <div class="mt-4">
          <canvas id="topicsChart" height="120"></canvas>
        </div>
      </div>

      <div class="modern-card p-6 lg:col-span-3 animate-fade-in" style="animation-delay: 0.3s">
        <div class="flex items-center justify-between gap-4 flex-wrap mb-4">
          <div class="flex items-center gap-3">
            <div class="w-10 h-10 bg-gradient-to-br from-orange-500 to-orange-600 rounded-xl flex items-center justify-center">
              <svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"></path>
              </svg>
            </div>
            <div>
              <div class="text-lg font-semibold text-[var(--text-primary)]">Framing Analysis</div>
              <div class="text-sm text-[var(--text-muted)]">Sentiment distribution across headlines</div>
            </div>
          </div>
          <div class="text-xs text-[var(--text-muted)] bg-[var(--bg-tertiary)] px-3 py-1 rounded-full">
            Headline cues only
          </div>
        </div>
        <div class="bg-[var(--bg-secondary)] rounded-lg p-4 mb-4">
          <div class="text-xs text-[var(--text-secondary)]">
            💡 Tip: Filter by a specific topic for cleaner sentiment analysis
          </div>
        </div>
        <div class="mt-4">
          <canvas id="skewChart" height="100"></canvas>
        </div>
      </div>

      <div class="modern-card p-6 lg:col-span-3 animate-fade-in" style="animation-delay: 0.4s">
        <div class="flex items-center justify-between gap-4 flex-wrap mb-4">
          <div class="flex items-center gap-3">
            <div class="w-10 h-10 bg-gradient-to-br from-emerald-500 to-emerald-600 rounded-xl flex items-center justify-center">
              <svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"></path>
              </svg>
            </div>
            <div>
              <div class="text-lg font-semibold text-[var(--text-primary)]">Topic Acceleration</div>
              <div class="text-sm text-[var(--text-muted)]">6h vs prior 6h momentum analysis</div>
            </div>
          </div>
          {% if lookback_hours < 12 %}
            <div class="text-xs text-[var(--accent-orange)] bg-orange-500/10 border border-orange-500/20 px-3 py-1 rounded-full">
              Fixed 6h windows
            </div>
          {% endif %}
        </div>
        <div class="overflow-x-auto">
          <table class="modern-table text-sm">
            <thead>
              <tr>
                <th class="text-left">Topic</th>
                <th class="text-right">Last 6h</th>
                <th class="text-right">Prior 6h</th>
                <th class="text-right">Delta</th>
                <th class="text-right">Ratio</th>
              </tr>
            </thead>
            <tbody>
              {% if acceleration %}
                {% for accel in acceleration %}
                  <tr>
                    <td class="font-semibold text-[var(--text-primary)]">{{ accel.topic }}</td>
                    <td class="text-right text-[var(--text-secondary)]">{{ accel.count_a }}</td>
                    <td class="text-right text-[var(--text-secondary)]">{{ accel.count_b }}</td>
                    <td class="text-right">
                      <span class="{% if accel.delta > 0 %}text-[var(--accent-green)] font-semibold{% elif accel.delta < 0 %}text-[var(--accent-red)]{% else %}text-[var(--text-muted)]{% endif %}">
                        {% if accel.delta > 0 %}+{% endif %}{{ accel.delta }}
                      </span>
                    </td>
                    <td class="text-right text-[var(--text-secondary)]">{{ "%.1f"|format(accel.ratio) }}</td>
                  </tr>
                {% endfor %}
              {% else %}
                <tr>
                  <td colspan="5" class="py-8 text-center text-[var(--text-muted)]">
                    <div class="flex flex-col items-center gap-2">
                      <svg class="w-8 h-8 text-[var(--text-muted)]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"></path>
                      </svg>
                      No acceleration data available
                    </div>
                  </td>
                </tr>
              {% endif %}
            </tbody>
          </table>
        </div>
      </div>

      <div class="modern-card p-6 lg:col-span-3 animate-fade-in" style="animation-delay: 0.5s">
        <div class="flex items-center gap-3 mb-4">
          <div class="w-10 h-10 bg-gradient-to-br from-cyan-500 to-cyan-600 rounded-xl flex items-center justify-center">
            <svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
            </svg>
          </div>
          <div>
            <div class="text-lg font-semibold text-[var(--text-primary)]">Source Health Monitor</div>
            <div class="text-sm text-[var(--text-muted)]">Feed reliability and error tracking</div>
          </div>
        </div>
        <div class="overflow-x-auto">
          <table class="modern-table text-sm">
            <thead>
              <tr>
                <th class="text-left">Source</th>
                <th class="text-left">Last Fetch</th>
                <th class="text-left">Status</th>
                <th class="text-right">Items Seen</th>
                <th class="text-right">Items Added</th>
              </tr>
            </thead>
            <tbody>
              {% for sh in source_health %}
                <tr>
                  <td>
                    <div class="font-semibold text-[var(--text-primary)]">{{ sh.publisher }}</div>
                    <div class="text-[var(--text-muted)] text-xs">{{ sh.feed_name }} • Category {{ sh.category }}</div>
                  </td>
                  <td class="text-[var(--text-secondary)]">
                    <span class="font-mono text-xs">{{ sh.last_fetch_utc or "—" }}</span>
                  </td>
                  <td>
                    {% if sh.last_error %}
                      <div class="flex items-center gap-2">
                        <div class="w-2 h-2 bg-red-500 rounded-full"></div>
                        <span class="text-[var(--accent-red)] font-medium">Error</span>
                      </div>
                      <div class="text-[var(--text-muted)] text-xs mt-1 max-w-xs truncate" title="{{ sh.last_error }}">{{ sh.last_error[:50] }}{% if sh.last_error|length > 50 %}...{% endif %}</div>
                    {% elif sh.last_ok_utc %}
                      <div class="flex items-center gap-2">
                        <div class="w-2 h-2 bg-green-500 rounded-full"></div>
                        <span class="text-[var(--accent-green)] font-medium">Healthy</span>
                      </div>
                      {% if sh.last_http_status %}
                        <div class="text-[var(--text-muted)] text-xs mt-1">HTTP {{ sh.last_http_status }}</div>
                      {% endif %}
                    {% else %}
                      <div class="flex items-center gap-2">
                        <div class="w-2 h-2 bg-gray-500 rounded-full"></div>
                        <span class="text-[var(--text-muted)]">Unknown</span>
                      </div>
                    {% endif %}
                  </td>
                  <td class="text-right text-[var(--text-secondary)]">{{ sh.items_seen_last_fetch }}</td>
                  <td class="text-right">
                    <span class="{% if sh.items_added_last_fetch > 0 %}text-[var(--accent-green)] font-semibold{% else %}text-[var(--text-secondary)]{% endif %}">
                      {{ sh.items_added_last_fetch }}
                    </span>
                  </td>
                </tr>
              {% endfor %}
            </tbody>
          </table>
        </div>
      </div>

      <div class="modern-card p-6 lg:col-span-3 animate-fade-in" style="animation-delay: 0.6s">
        <div class="flex items-center gap-3 mb-4">
          <div class="w-10 h-10 bg-gradient-to-br from-indigo-500 to-indigo-600 rounded-xl flex items-center justify-center">
            <svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"></path>
            </svg>
          </div>
          <div>
            <div class="text-lg font-semibold text-[var(--text-primary)]">Latest News Feed</div>
            <div class="text-sm text-[var(--text-muted)]">Real-time financial news aggregation</div>
          </div>
        </div>
        <div class="space-y-4">
          {% for it in items %}
            <div class="border border-[var(--border-primary)] rounded-lg p-4 hover:border-[var(--border-secondary)] transition-colors">
              <div class="flex flex-col md:flex-row md:items-start gap-3">
                <div class="md:w-64 shrink-0">
                  <div class="text-xs text-[var(--text-muted)] mb-1">
                    {{ it.publisher }} • {{ it.feed_name }}
                  </div>
                  <div class="text-xs text-[var(--text-secondary)] font-mono">
                    {{ it.published_at or it.fetched_at }}
                  </div>
                  <div class="mt-2">
                    <span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-[var(--bg-tertiary)] text-[var(--text-secondary)]">
                      {% if it.category == "A" %}📈 Market News
                      {% elif it.category == "B" %}📰 Interpretive/Opinion
                      {% elif it.category == "C" %}🏛️ Macro/Policy Anchors
                      {% elif it.category == "D" %}💼 Practitioner Commentary
                      {% else %}📊 Other{% endif %}
                    </span>
                  </div>
                </div>
                <div class="flex-1 min-w-0">
                  <h3 class="font-semibold text-[var(--text-primary)] hover:text-[var(--accent-blue)] transition-colors mb-2">
                    <a href="{{ it.url }}" target="_blank" rel="noreferrer" class="block">
                      {{ it.title }}
                    </a>
                  </h3>
                  <div class="flex flex-wrap gap-2 mb-3">
                    <span class="badge badge-{{ it.direction|lower }}">{{ it.direction }}</span>
                    <span class="badge badge-neutral">{{ it.urgency }}</span>
                    <span class="badge badge-neutral">{{ it.mode }}</span>
                    {% for tag in it.asset_classes %}
                      <span class="badge badge-asset">{{ tag }}</span>
                    {% endfor %}
                    {% for tag in it.geo_tags %}
                      <span class="badge badge-geo">{{ tag }}</span>
                    {% endfor %}
                  </div>
                  {% if it.summary %}
                    <p class="text-[var(--text-secondary)] text-sm line-clamp-2">{{ it.summary }}</p>
                  {% endif %}
                </div>
              </div>
            </div>
          {% endfor %}
        </div>
        {% if not items %}
          <div class="text-center py-12">
            <svg class="w-16 h-16 text-[var(--text-muted)] mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"></path>
            </svg>
            <p class="text-[var(--text-muted)] text-lg">No news items found</p>
            <p class="text-[var(--text-secondary)] text-sm mt-1">Try adjusting your filters or check back later</p>
          </div>
        {% endif %}
      </div>
    </div>
  </div>

<script>
  // Modern Chart.js configuration
  Chart.defaults.color = '#cbd5e1';
  Chart.defaults.borderColor = 'rgba(148,163,184,0.12)';
  Chart.defaults.font.family = 'ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
  Chart.defaults.font.size = 12;

  // Custom color palettes
  const chartColors = {
    primary: ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4', '#84cc16', '#f97316'],
    gradients: [
      'linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%)',
      'linear-gradient(135deg, #10b981 0%, #047857 100%)',
      'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)',
      'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)'
    ]
  };

  // Topic counts chart
  const topicLabels = {{ topic_labels | safe }};
  const topicCounts = {{ topic_counts | safe }};

  const topicsCtx = document.getElementById("topicsChart").getContext("2d");
  const topicsGradient = topicsCtx.createLinearGradient(0, 0, 0, 400);
  topicsGradient.addColorStop(0, 'rgba(59, 130, 246, 0.8)');
  topicsGradient.addColorStop(1, 'rgba(59, 130, 246, 0.1)');

  new Chart(topicsCtx, {
    type: "bar",
    data: {
      labels: topicLabels,
      datasets: [{
        label: "Articles",
        data: topicCounts,
        backgroundColor: topicsGradient,
        borderColor: '#3b82f6',
        borderWidth: 1,
        borderRadius: 4,
        borderSkipped: false,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: {
        duration: 1000,
        easing: 'easeOutQuart'
      },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: 'rgba(15, 23, 42, 0.9)',
          titleColor: '#f8fafc',
          bodyColor: '#cbd5e1',
          borderColor: '#334155',
          borderWidth: 1,
          cornerRadius: 8,
          displayColors: false,
          callbacks: {
            title: function(context) {
              return `Topic: ${context[0].label}`;
            },
            label: function(context) {
              return `Articles: ${context.parsed.y}`;
            }
          }
        }
      },
      scales: {
        x: {
          ticks: {
            color: "#cbd5e1",
            font: { size: 11 },
            maxRotation: 45
          },
          grid: {
            color: "rgba(148,163,184,0.08)",
            borderColor: "rgba(148,163,184,0.2)"
          }
        },
        y: {
          beginAtZero: true,
          ticks: {
            color: "#cbd5e1",
            font: { size: 11 },
            precision: 0
          },
          grid: {
            color: "rgba(148,163,184,0.08)",
            borderColor: "rgba(148,163,184,0.2)"
          }
        }
      },
      onHover: (event, activeElements) => {
        event.native.target.style.cursor = activeElements.length > 0 ? 'pointer' : 'default';
      }
    }
  });

  // Framing skew chart
  const skew = {{ skew | safe }};
  const skewCtx = document.getElementById("skewChart").getContext("2d");

  // Create gradients for each bar
  const createGradient = (ctx, color1, color2) => {
    const gradient = ctx.createLinearGradient(0, 0, 0, 100);
    gradient.addColorStop(0, color1);
    gradient.addColorStop(1, color2);
    return gradient;
  };

  const skewGradients = [
    createGradient(skewCtx, 'rgba(16, 185, 129, 0.8)', 'rgba(16, 185, 129, 0.3)'), // positive
    createGradient(skewCtx, 'rgba(239, 68, 68, 0.8)', 'rgba(239, 68, 68, 0.3)'),   // negative
    createGradient(skewCtx, 'rgba(148, 163, 184, 0.8)', 'rgba(148, 163, 184, 0.3)'), // neutral
    createGradient(skewCtx, 'rgba(245, 158, 11, 0.8)', 'rgba(245, 158, 11, 0.3)')    // mixed
  ];

  new Chart(skewCtx, {
    type: "bar",
    data: {
      labels: ["Positive", "Negative", "Neutral", "Mixed"],
      datasets: [{
        label: "Articles",
        data: [skew.pos, skew.neg, skew.neutral, skew.mixed],
        backgroundColor: skewGradients,
        borderColor: ['#10b981', '#ef4444', '#94a3b8', '#f59e0b'],
        borderWidth: 1,
        borderRadius: 6,
        borderSkipped: false,
        hoverBackgroundColor: ['#059669', '#dc2626', '#64748b', '#d97706']
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: {
        duration: 1200,
        easing: 'easeOutQuart',
        delay: function(context) {
          return context.dataIndex * 100;
        }
      },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: 'rgba(15, 23, 42, 0.9)',
          titleColor: '#f8fafc',
          bodyColor: '#cbd5e1',
          borderColor: '#334155',
          borderWidth: 1,
          cornerRadius: 8,
          displayColors: false,
          callbacks: {
            title: function(context) {
              return `Sentiment: ${context[0].label}`;
            },
            label: function(context) {
              const total = skew.pos + skew.neg + skew.neutral + skew.mixed;
              const percentage = total > 0 ? ((context.parsed.y / total) * 100).toFixed(1) : 0;
              return `Articles: ${context.parsed.y} (${percentage}%)`;
            }
          }
        }
      },
      scales: {
        x: {
          ticks: {
            color: "#cbd5e1",
            font: { size: 11, weight: '500' }
          },
          grid: {
            color: "rgba(148,163,184,0.08)",
            borderColor: "rgba(148,163,184,0.2)"
          }
        },
        y: {
          beginAtZero: true,
          ticks: {
            color: "#cbd5e1",
            font: { size: 11 },
            precision: 0
          },
          grid: {
            color: "rgba(148,163,184,0.08)",
            borderColor: "rgba(148,163,184,0.2)"
          }
        }
      },
      onHover: (event, activeElements) => {
        event.native.target.style.cursor = activeElements.length > 0 ? 'pointer' : 'default';
      }
    }
  });

  // Enhanced UX and Modern Web Features
  document.addEventListener('DOMContentLoaded', function() {
    // Performance: Intersection Observer for lazy loading animations
    const observerOptions = {
      threshold: 0.1,
      rootMargin: '50px 0px'
    };

    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry, index) => {
        if (entry.isIntersecting) {
          entry.target.style.animationDelay = `${index * 100}ms`;
          entry.target.classList.add('animate-fade-in');
          observer.unobserve(entry.target);
        }
      });
    }, observerOptions);

    // Observe cards for lazy animations
    const cards = document.querySelectorAll('.modern-card');
    cards.forEach(card => observer.observe(card));

    // Enhanced form submission with loading states
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
      form.addEventListener('submit', function(e) {
        const button = form.querySelector('button[type="submit"]');
        if (button) {
          const originalHTML = button.innerHTML;
          button.innerHTML = `
            <span class="flex items-center gap-2">
              <svg class="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              Applying filters...
            </span>
          `;
          button.classList.add('btn-loading');
          button.disabled = true;

          // Auto-reset after 3 seconds (handles both success and error cases)
          setTimeout(() => {
            button.innerHTML = originalHTML;
            button.classList.remove('btn-loading');
            button.disabled = false;
          }, 3000);
        }
      });
    });

    // Enhanced keyboard navigation and accessibility
    document.addEventListener('keydown', function(e) {
      // Enhanced form navigation
      if (e.key === 'Enter' && e.target.matches('input, select')) {
        e.preventDefault();
        const form = e.target.closest('form');
        if (form) {
          const submitBtn = form.querySelector('button[type="submit"]');
          if (submitBtn && !submitBtn.disabled) {
            submitBtn.focus();
            setTimeout(() => submitBtn.click(), 100);
          }
        }
      }

      // Skip to main content (accessibility)
      if (e.key === '/' && !e.target.matches('input, select, textarea')) {
        e.preventDefault();
        const mainContent = document.querySelector('main') || document.querySelector('.grid');
        if (mainContent) {
          mainContent.focus();
          mainContent.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
      }
    });

    // Add ARIA labels and roles for accessibility
    const statusCards = document.querySelectorAll('.modern-card');
    statusCards.forEach((card, index) => {
      card.setAttribute('role', 'region');
      card.setAttribute('aria-labelledby', `card-title-${index}`);
      const title = card.querySelector('h2, .text-lg');
      if (title) {
        title.id = `card-title-${index}`;
      }
    });

    // Enhanced responsive chart resizing with debouncing
    let resizeTimeout;
    window.addEventListener('resize', function() {
      clearTimeout(resizeTimeout);
      resizeTimeout = setTimeout(function() {
        // Force chart resize for better responsiveness
        const charts = document.querySelectorAll('canvas');
        charts.forEach(canvas => {
          const chart = Chart.getChart(canvas);
          if (chart) {
            chart.resize();
          }
        });
      }, 250);
    });

    // Performance: Preload critical resources
    const preloadLinks = [
      'https://cdn.tailwindcss.com',
      'https://cdn.jsdelivr.net/npm/chart.js@4.4.0'
    ];

    preloadLinks.forEach(url => {
      const link = document.createElement('link');
      link.rel = 'preload';
      link.href = url;
      link.as = 'script';
      document.head.appendChild(link);
    });

    // Add service worker for caching (if supported)
    if ('serviceWorker' in navigator) {
      window.addEventListener('load', function() {
        // Could register a service worker here for caching static assets
        // navigator.serviceWorker.register('/sw.js');
      });
    }

    // Enhanced error handling
    window.addEventListener('error', function(e) {
      console.error('JavaScript error:', e.error);
      // Could send to error tracking service
    });

    window.addEventListener('unhandledrejection', function(e) {
      console.error('Unhandled promise rejection:', e.reason);
      // Could send to error tracking service
    });

    // Performance monitoring (basic)
    const perfData = performance.getEntriesByType('navigation')[0];
    if (perfData) {
      console.log(`Page load time: ${perfData.loadEventEnd - perfData.fetchStart}ms`);
    }

    // Add touch gesture support for mobile
    let touchStartY = 0;
    let touchEndY = 0;

    document.addEventListener('touchstart', function(e) {
      touchStartY = e.changedTouches[0].screenY;
    });

    document.addEventListener('touchend', function(e) {
      touchEndY = e.changedTouches[0].screenY;
      const diff = touchStartY - touchEndY;

      // Swipe up to scroll to top (on mobile)
      if (diff > 100 && window.innerWidth < 768) {
        window.scrollTo({ top: 0, behavior: 'smooth' });
      }
    });

    // Enhanced tooltips for better UX
    const tooltipElements = document.querySelectorAll('[title]');
    tooltipElements.forEach(el => {
      el.setAttribute('aria-label', el.getAttribute('title'));
    });

    // Auto-focus management
    const focusableElements = 'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])';
    const firstFocusable = document.querySelector(focusableElements);

    // Skip link for accessibility
    const skipLink = document.createElement('a');
    skipLink.href = '#main-content';
    skipLink.textContent = 'Skip to main content';
    skipLink.className = 'sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 bg-blue-600 text-white px-4 py-2 rounded-lg z-50';
    skipLink.style.cssText = `
      position: absolute;
      top: -40px;
      left: 6px;
      background: #2563eb;
      color: white;
      padding: 8px 16px;
      border-radius: 8px;
      text-decoration: none;
      z-index: 1000;
      transition: top 0.2s;
    `;
    skipLink.addEventListener('focus', function() {
      this.style.top = '6px';
    });
    skipLink.addEventListener('blur', function() {
      this.style.top = '-40px';
    });
    document.body.insertBefore(skipLink, document.body.firstChild);

    // Add main content landmark
    const mainGrid = document.querySelector('.grid');
    if (mainGrid) {
      mainGrid.id = 'main-content';
      mainGrid.setAttribute('role', 'main');
    }

    // Performance: Defer non-critical JavaScript
    setTimeout(() => {
      // Any non-critical enhancements can go here
      console.log('Enhanced UX features loaded');
    }, 100);
  });

  // Progressive enhancement: Check for modern features
  if ('IntersectionObserver' in window) {
    // Use modern intersection observer
  } else {
    // Fallback for older browsers
    const cards = document.querySelectorAll('.modern-card');
    cards.forEach(card => card.classList.add('animate-fade-in'));
  }

  // Feature detection and graceful degradation
  const supportsCSSGrid = CSS.supports('display', 'grid');
  const supportsCSSCustomProperties = CSS.supports('color', 'var(--test)');

  if (!supportsCSSGrid) {
    console.warn('CSS Grid not supported, falling back to flexbox');
    // Could add fallback styles here
  }

  if (!supportsCSSCustomProperties) {
    console.warn('CSS Custom Properties not supported, using fallback styles');
    // Could add fallback styles here
  }
</script>
</body>
</html>
"""


def create_app(app_title: str, default_lookback_hours: int, fetch_interval_seconds: int) -> Flask:
    """Create and configure the Flask application."""
    app = Flask(__name__)
    _stop_event = threading.Event()
    _worker_thread: Optional[threading.Thread] = None

    @app.before_request
    def _before_request() -> None:
        _ = db.get_db()

    @app.teardown_appcontext
    def _teardown(exc: Optional[BaseException]) -> None:
        db_conn = g.pop("db", None)
        if db_conn is not None:
            db_conn.close()

    def query_items(lookback_hours: int, category: Optional[str], topic: Optional[str]) -> List[Dict[str, Any]]:
        db_conn = db.get_db()
        since = utils.utcnow() - timedelta(hours=lookback_hours)
        where = ["(published_at IS NULL AND fetched_at >= ?) OR (published_at >= ?)"]
        params: List[Any] = [since.isoformat(), since.isoformat()]

        if category:
            where.append("s.category = ?")
            params.append(category)
        if topic:
            where.append("it.tag = ?")
            params.append(topic)

        # Get items with their tags
        sql_items = f"""
        SELECT i.*, s.publisher, s.feed_name, s.category,
               sig.direction, sig.urgency, sig.mode
        FROM items i
        JOIN sources s ON s.source_id = i.source_id
        LEFT JOIN signals sig ON sig.item_id = i.item_id
        LEFT JOIN item_tags it ON it.item_id = i.item_id
        WHERE {" AND ".join(where)}
        GROUP BY i.item_id
        ORDER BY COALESCE(i.published_at, i.fetched_at) DESC
        LIMIT 500
        """
        items = db_conn.execute(sql_items, params).fetchall()

        # Get tags for each item
        item_ids = [item["item_id"] for item in items]
        if item_ids:
            placeholders = ",".join("?" * len(item_ids))
            sql_tags = f"""
            SELECT it.item_id, it.tag, t.tag_type
            FROM item_tags it
            JOIN tags t ON t.tag = it.tag
            WHERE it.item_id IN ({placeholders})
            ORDER BY it.item_id, t.tag_type, it.tag
            """
            tags_rows = db_conn.execute(sql_tags, item_ids).fetchall()

            # Group tags by item_id and tag_type
            tags_by_item = {}
            for row in tags_rows:
                item_id = row["item_id"]
                if item_id not in tags_by_item:
                    tags_by_item[item_id] = {"topics": [], "asset_classes": [], "geo_tags": []}
                tag_type = row["tag_type"]
                if tag_type == "topic":
                    tags_by_item[item_id]["topics"].append(row["tag"])
                elif tag_type == "asset_class":
                    tags_by_item[item_id]["asset_classes"].append(row["tag"])
                elif tag_type == "geo":
                    tags_by_item[item_id]["geo_tags"].append(row["tag"])

            # Add tags to items (convert Row objects to dicts for mutability)
            items_with_tags = []
            for item in items:
                item_dict = dict(item)  # Convert Row to dict
                item_id = item_dict["item_id"]
                if item_id in tags_by_item:
                    item_tags = tags_by_item[item_id]
                    item_dict["asset_classes"] = item_tags["asset_classes"]
                    item_dict["geo_tags"] = item_tags["geo_tags"]
                else:
                    item_dict["asset_classes"] = []
                    item_dict["geo_tags"] = []
                items_with_tags.append(item_dict)

            items = items_with_tags

        return items

    def query_topic_counts(lookback_hours: int, category: Optional[str]) -> List[Tuple[str, int]]:
        db_conn = db.get_db()
        since = utils.utcnow() - timedelta(hours=lookback_hours)
        params: List[Any] = [since.isoformat(), since.isoformat()]
        where = ["(i.published_at IS NULL AND i.fetched_at >= ?) OR (i.published_at >= ?)"]
        if category:
            where.append("s.category = ?")
            params.append(category)

        sql = f"""
        SELECT it.tag as tag, COUNT(DISTINCT i.item_id) as n
        FROM items i
        JOIN sources s ON s.source_id = i.source_id
        JOIN item_tags it ON it.item_id = i.item_id
        WHERE {" AND ".join(where)}
        GROUP BY it.tag
        ORDER BY n DESC
        LIMIT 20
        """
        rows = db_conn.execute(sql, params).fetchall()
        return [(r["tag"], int(r["n"])) for r in rows]

    def query_framing_skew(lookback_hours: int, topic: Optional[str]) -> Dict[str, int]:
        db_conn = db.get_db()
        since = utils.utcnow() - timedelta(hours=lookback_hours)
        params: List[Any] = [since.isoformat(), since.isoformat()]
        where = ["(i.published_at IS NULL AND i.fetched_at >= ?) OR (i.published_at >= ?)"]
        if topic:
            where.append("it.tag = ?")
            params.append(topic)

        sql = f"""
        SELECT sig.direction as direction, COUNT(DISTINCT i.item_id) as n
        FROM items i
        LEFT JOIN signals sig ON sig.item_id = i.item_id
        LEFT JOIN item_tags it ON it.item_id = i.item_id
        WHERE {" AND ".join(where)}
        GROUP BY sig.direction
        """
        rows = db_conn.execute(sql, params).fetchall()
        out = {"pos": 0, "neg": 0, "neutral": 0, "mixed": 0}
        for r in rows:
            k = r["direction"] or "neutral"
            if k not in out:
                continue
            out[k] = int(r["n"])
        return out

    def query_acceleration(category: Optional[str]) -> List[Dict[str, Any]]:
        """
        Compute topic acceleration: last 6h vs prior 6h (6-12h ago).
        Returns list of dicts with: topic, count_a, count_b, delta, ratio
        """
        db_conn = db.get_db()
        now = utils.utcnow()
        window_a_start = (now - timedelta(hours=6)).isoformat()
        window_b_start = (now - timedelta(hours=12)).isoformat()
        window_b_end = window_a_start
        
        # Build params for window A (last 6h)
        params_a: List[Any] = [window_a_start, window_a_start]
        where_a = ["(i.published_at IS NULL AND i.fetched_at >= ?) OR (i.published_at >= ?)"]
        category_join_a = ""
        if category:
            category_join_a = "JOIN sources s ON s.source_id = i.source_id"
            where_a.append("s.category = ?")
            params_a.append(category)
        
        # Build params for window B (6-12h ago)
        params_b: List[Any] = [window_b_start, window_b_start, window_b_end, window_b_end]
        where_b = ["(i.published_at IS NULL AND i.fetched_at >= ? AND i.fetched_at < ?) OR (i.published_at >= ? AND i.published_at < ?)"]
        category_join_b = ""
        if category:
            category_join_b = "JOIN sources s ON s.source_id = i.source_id"
            where_b.append("s.category = ?")
            params_b.append(category)
        
        # Count items in window A (last 6h) per topic
        sql_a = f"""
        SELECT it.tag as topic, COUNT(DISTINCT i.item_id) as count_a
        FROM items i
        {category_join_a}
        JOIN item_tags it ON it.item_id = i.item_id
        WHERE {" AND ".join(where_a)}
        GROUP BY it.tag
        """
        
        # Count items in window B (6-12h ago) per topic
        sql_b = f"""
        SELECT it.tag as topic, COUNT(DISTINCT i.item_id) as count_b
        FROM items i
        {category_join_b}
        JOIN item_tags it ON it.item_id = i.item_id
        WHERE {" AND ".join(where_b)}
        GROUP BY it.tag
        """
        
        # Get counts for both windows
        rows_a = db_conn.execute(sql_a, params_a).fetchall()
        rows_b = db_conn.execute(sql_b, params_b).fetchall()
        
        # Build dicts
        counts_a = {r["topic"]: int(r["count_a"]) for r in rows_a}
        counts_b = {r["topic"]: int(r["count_b"]) for r in rows_b}
        
        # Combine and compute delta/ratio
        all_topics = set(counts_a.keys()) | set(counts_b.keys())
        results = []
        for topic in all_topics:
            count_a = counts_a.get(topic, 0)
            count_b = counts_b.get(topic, 0)
            delta = count_a - count_b
            # Ratio: count_a / count_b if count_b > 0, else count_a
            ratio = count_a / count_b if count_b > 0 else float(count_a) if count_a > 0 else 0.0
            results.append({
                "topic": topic,
                "count_a": count_a,
                "count_b": count_b,
                "delta": delta,
                "ratio": ratio,
            })
        
        # Sort by delta DESC, then ratio DESC
        results.sort(key=lambda x: (x["delta"], x["ratio"]), reverse=True)
        return results[:15]  # Limit 15 rows

    def query_source_health() -> List[sqlite3.Row]:
        """Get top 10 sources by recent errors or status."""
        db_conn = db.get_db()
        sql = """
        SELECT ss.*, s.publisher, s.feed_name, s.category
        FROM source_status ss
        JOIN sources s ON s.source_id = ss.source_id
        WHERE ss.last_fetch_utc IS NOT NULL
        ORDER BY 
          CASE WHEN ss.last_error IS NOT NULL THEN 0 ELSE 1 END,
          ss.last_fetch_utc DESC
        LIMIT 10
        """
        return db_conn.execute(sql).fetchall()

    @app.route("/")
    def index() -> Response:
        lookback = int(request.args.get("lookback", default_lookback_hours))
        category = request.args.get("category") or None
        topic = (request.args.get("topic") or "").strip() or None

        items = query_items(lookback, category, topic)
        topic_counts = query_topic_counts(lookback, category)
        skew = query_framing_skew(lookback, topic)
        source_health = query_source_health()
        acceleration = query_acceleration(category)

        labels = [t for (t, n) in topic_counts]
        counts = [n for (t, n) in topic_counts]

        status = ingest.get_fetch_status()
        return render_template_string(
            TEMPLATE,
            title=app_title,
            lookback_hours=lookback,
            category=category,
            topic=topic,
            items=items,
            topic_labels=labels,
            topic_counts=counts,
            skew=skew,
            status=type("S", (), status),
            source_health=source_health,
            acceleration=acceleration,
        )

    @app.route("/fetch-now")
    def fetch_now() -> Response:
        ingest.fetch_once()
        return redirect(url_for("index"))

    @app.route("/healthz")
    def healthz() -> Response:
        """Health check endpoint. Returns 200 if last fetch succeeded within 2x interval, else 503."""
        status = ingest.get_fetch_status()
        fetch_interval_seconds_double = fetch_interval_seconds * 2

        if status["last_error"]:
            return Response(
                f"Unhealthy: {status['last_error']}",
                status=503,
                mimetype="text/plain"
            )

        if not status["last_run_utc"]:
            return Response(
                "Unhealthy: No fetch has completed yet",
                status=503,
                mimetype="text/plain"
            )

        # Check if last fetch was within 2x interval
        from datetime import datetime, timezone
        last_run = datetime.fromisoformat(status["last_run_utc"])
        now = utils.utcnow()
        elapsed = (now - last_run).total_seconds()

        if elapsed > fetch_interval_seconds_double:
            return Response(
                f"Unhealthy: Last fetch was {elapsed:.0f}s ago (threshold: {fetch_interval_seconds_double}s)",
                status=503,
                mimetype="text/plain"
            )

        return Response("OK", status=200, mimetype="text/plain")

    @app.route("/admin/maintenance", methods=["GET", "POST"])
    def admin_maintenance() -> Response:
        """Database maintenance page."""
        if request.method == "POST":
            action = request.form.get("action")
            if action == "cleanup":
                cleanup_stats = db.run_cleanup(db.get_db())
                # Redirect back with success message
                return redirect(url_for("admin_maintenance", success=f"Cleanup completed: {cleanup_stats['items_deleted']} items deleted"))
            elif action == "vacuum":
                conn = db.get_db()
                conn.execute("VACUUM")
                return redirect(url_for("admin_maintenance", success="VACUUM completed"))
            elif action == "archive":
                archive_days = int(request.form.get("archive_days", 365))
                try:
                    conn = db.get_db()
                    archive_path = db.archive_old_items(conn, archive_days)
                    return redirect(url_for("admin_maintenance", success=f"Archive created: {archive_path}"))
                except ValueError as e:
                    return redirect(url_for("admin_maintenance", error=str(e)))

        # GET request - show maintenance page
        db_size = db.get_db_file_size()
        retention_days = db.get_retention_days()
        last_cleanup = db.get_maintenance_state(db.get_db(), "last_cleanup")

        # Format file size
        if db_size < 1024:
            size_str = f"{db_size} bytes"
        elif db_size < 1024 * 1024:
            size_str = f"{db_size / 1024:.1f} KB"
        else:
            size_str = f"{db_size / (1024 * 1024):.1f} MB"

        success_msg = request.args.get("success")

        # Use Jinja2 templating like the main dashboard
        template = f"""
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>Database Maintenance — RSS Dashboard</title>
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-950 text-slate-100">
  <div class="max-w-4xl mx-auto p-4 md:p-8">
    <div class="mb-6">
      <a href="{url_for('index')}" class="text-indigo-300 hover:text-indigo-200">&larr; Back to Dashboard</a>
    </div>

    <h1 class="text-2xl md:text-3xl font-semibold mb-6">Database Maintenance</h1>

    {{% if success_msg %}}
      <div class="bg-green-900 border border-green-700 rounded-xl p-4 mb-6">
        <div class="text-green-200">{{{{ success_msg }}}}</div>
      </div>
    {{% endif %}}

    <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
      <div class="bg-slate-900 border border-slate-800 rounded-2xl p-6">
        <h2 class="text-lg font-medium mb-4">Database Status</h2>
        <div class="space-y-3">
          <div class="flex justify-between">
            <span class="text-slate-300">File size:</span>
            <span class="font-medium">{size_str}</span>
          </div>
          <div class="flex justify-between">
            <span class="text-slate-300">Retention period:</span>
            <span class="font-medium">{retention_days} days</span>
          </div>
          <div class="flex justify-between">
            <span class="text-slate-300">Last cleanup:</span>
            <span class="font-medium">{last_cleanup or "Never"}</span>
          </div>
        </div>
      </div>

      <div class="bg-slate-900 border border-slate-800 rounded-2xl p-6">
        <h2 class="text-lg font-medium mb-4">Cleanup & Maintenance</h2>
        <div class="space-y-4">
          <form method="post" class="inline">
            <input type="hidden" name="action" value="cleanup" />
            <button type="submit" class="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 rounded-xl font-medium">
              Run Cleanup Now
            </button>
          </form>
          <div class="text-sm text-slate-400">
            Deletes items older than {retention_days} days based on published date.
          </div>

          <hr class="border-slate-700" />

          <form method="post" class="inline">
            <input type="hidden" name="action" value="vacuum" />
            <button type="submit" class="px-4 py-2 bg-orange-600 hover:bg-orange-500 rounded-xl font-medium">
              Run VACUUM
            </button>
          </form>
          <div class="text-sm text-slate-400">
            Reclaims disk space. May take time on large databases.
          </div>
        </div>
      </div>

      <div class="bg-slate-900 border border-slate-800 rounded-2xl p-6">
        <h2 class="text-lg font-medium mb-4">Archiving</h2>
        <div class="space-y-4">
          <form method="post" class="space-y-3">
            <input type="hidden" name="action" value="archive" />
            <div>
              <label class="block text-sm text-slate-300 mb-1">Archive items older than:</label>
              <select name="archive_days" class="bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-sm w-full">
                <option value="365">1 year (365 days)</option>
                <option value="180">6 months (180 days)</option>
                <option value="90">3 months (90 days)</option>
                <option value="30">1 month (30 days)</option>
              </select>
            </div>
            <button type="submit" class="px-4 py-2 bg-green-600 hover:bg-green-500 rounded-xl font-medium w-full">
              Create Archive
            </button>
          </form>
          <div class="text-sm text-slate-400">
            Exports old data to compressed JSON file before deletion. Useful for historical analysis.
          </div>
        </div>
      </div>
    </div>
  </div>
</body>
</html>
"""
        return render_template_string(template, success_msg=success_msg)

    @app.route("/debug/rules")
    def debug_rules() -> Response:
        """Debug endpoint returning JSON of rule hit counts over last 24h."""
        import json
        from datetime import datetime, timedelta

        db_conn = db.get_db()
        since = utils.utcnow() - timedelta(hours=24)

        # Get all items from last 24h
        sql_items = """
        SELECT i.item_id, i.title
        FROM items i
        WHERE (i.published_at IS NOT NULL AND i.published_at >= ?) OR
              (i.published_at IS NULL AND i.fetched_at >= ?)
        """
        items = db_conn.execute(sql_items, (since.isoformat(), since.isoformat())).fetchall()

        # Count rule hits
        rule_counts = {
            "topics": {tag: 0 for tag in rules.TOPIC_RULES.keys()},
            "asset_classes": {tag: 0 for tag in rules.ASSET_CLASS_RULES.keys()},
            "geo": {tag: 0 for tag in rules.GEO_RULES.keys()},
            "total_items": len(items)
        }

        for item in items:
            title = item["title"] or ""

            # Count topic hits
            for tag in rules.tag_topics(title):
                if tag in rule_counts["topics"]:
                    rule_counts["topics"][tag] += 1

            # Count asset class hits
            for tag in rules.tag_asset_class(title):
                if tag in rule_counts["asset_classes"]:
                    rule_counts["asset_classes"][tag] += 1

            # Count geo hits
            for tag in rules.tag_geo(title):
                if tag in rule_counts["geo"]:
                    rule_counts["geo"][tag] += 1

        return Response(
            json.dumps(rule_counts, indent=2),
            status=200,
            mimetype="application/json"
        )

    def start_worker_if_needed() -> None:
        nonlocal _worker_thread
        if _worker_thread and _worker_thread.is_alive():
            return
        _worker_thread = threading.Thread(
            target=ingest.fetch_loop,
            args=(_stop_event, fetch_interval_seconds),
            daemon=True,
        )
        _worker_thread.start()

    start_worker_if_needed()
    return app
