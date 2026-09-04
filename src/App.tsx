import React, { useState } from 'react';
import { 
  Zap, 
  Activity, 
  FileSpreadsheet, 
  Settings2, 
  Download, 
  Sun, 
  Moon, 
  Terminal, 
  ShieldCheck, 
  Sliders, 
  Cpu,
  ArrowUpRight,
  Code
} from 'lucide-react';

export default function App() {
  const [theme, setTheme] = useState<'dark' | 'light'>('dark');
  const [activeTab, setActiveTab] = useState<'overview' | 'features' | 'code' | 'export'>('overview');

  const isDark = theme === 'dark';

  return (
    <div id="app_root" className={`min-h-screen transition-colors duration-200 ${isDark ? 'bg-[#0f1115] text-[#e2e8f0]' : 'bg-[#f8fafc] text-[#0f172a]'}`}>
      {/* Top Header Bar */}
      <header id="main_header" className={`border-b px-6 py-4 transition-colors ${isDark ? 'bg-[#16181d] border-[#272a31]' : 'bg-white border-[#e2e8f0]'}`}>
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-sky-500/20 text-sky-400 flex items-center justify-center border border-sky-500/30">
              <Zap className="w-6 h-6 text-sky-400" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-xl font-bold tracking-tight">ET PS LAB-HP Controller</h1>
                <span className="px-2 py-0.5 rounded text-xs font-semibold bg-sky-500/10 text-sky-400 border border-sky-500/20">v5.0 Enterprise</span>
              </div>
              <p className={`text-xs ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>High-Power DC Supply Controller & Historical Session Analytics</p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button
              id="btn_theme_toggle_web"
              onClick={() => setTheme(isDark ? 'light' : 'dark')}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-medium border transition-colors ${
                isDark 
                  ? 'bg-[#1f232b] hover:bg-[#2b303c] border-[#2e3340] text-amber-300' 
                  : 'bg-slate-100 hover:bg-slate-200 border-slate-300 text-slate-800'
              }`}
            >
              {isDark ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
              <span>{isDark ? '☀️ Light Mode' : '🌙 Dark Mode'}</span>
            </button>

            <a
              id="btn_view_py_file"
              href="#launch"
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium bg-sky-600 hover:bg-sky-500 text-white transition-colors shadow-sm"
            >
              <Terminal className="w-3.5 h-3.5" />
              <span>Launch Desktop GUI</span>
            </a>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="max-w-7xl mx-auto px-6 py-8">
        {/* Navigation Tabs */}
        <div className={`flex border-b mb-8 ${isDark ? 'border-[#272a31]' : 'border-slate-200'}`}>
          <button
            id="tab_nav_overview"
            onClick={() => setActiveTab('overview')}
            className={`flex items-center gap-2 px-5 py-3 text-sm font-semibold border-b-2 -mb-px transition-colors ${
              activeTab === 'overview'
                ? 'border-sky-500 text-sky-500'
                : isDark ? 'border-transparent text-slate-400 hover:text-slate-200' : 'border-transparent text-slate-500 hover:text-slate-900'
            }`}
          >
            <Activity className="w-4 h-4" />
            <span>Architecture & Capabilities</span>
          </button>

          <button
            id="tab_nav_export"
            onClick={() => setActiveTab('export')}
            className={`flex items-center gap-2 px-5 py-3 text-sm font-semibold border-b-2 -mb-px transition-colors ${
              activeTab === 'export'
                ? 'border-sky-500 text-sky-500'
                : isDark ? 'border-transparent text-slate-400 hover:text-slate-200' : 'border-transparent text-slate-500 hover:text-slate-900'
            }`}
          >
            <Download className="w-4 h-4" />
            <span>Multi-Format Export & Customization</span>
          </button>

          <button
            id="tab_nav_features"
            onClick={() => setActiveTab('features')}
            className={`flex items-center gap-2 px-5 py-3 text-sm font-semibold border-b-2 -mb-px transition-colors ${
              activeTab === 'features'
                ? 'border-sky-500 text-sky-500'
                : isDark ? 'border-transparent text-slate-400 hover:text-slate-200' : 'border-transparent text-slate-500 hover:text-slate-900'
            }`}
          >
            <Sliders className="w-4 h-4" />
            <span>Theme & Presentation Engine</span>
          </button>

          <button
            id="tab_nav_code"
            onClick={() => setActiveTab('code')}
            className={`flex items-center gap-2 px-5 py-3 text-sm font-semibold border-b-2 -mb-px transition-colors ${
              activeTab === 'code'
                ? 'border-sky-500 text-sky-500'
                : isDark ? 'border-transparent text-slate-400 hover:text-slate-200' : 'border-transparent text-slate-500 hover:text-slate-900'
            }`}
          >
            <Code className="w-4 h-4" />
            <span>Desktop App Code (PyQt6)</span>
          </button>
        </div>

        {/* Tab 1: Overview */}
        {activeTab === 'overview' && (
          <div className="space-y-8">
            {/* Highlights Grid */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className={`p-4 rounded-xl border ${isDark ? 'bg-[#16181d] border-[#272a31]' : 'bg-white border-slate-200 shadow-sm'}`}>
                <div className="text-xs uppercase font-bold text-sky-400 mb-1">Voltage Output</div>
                <div className="text-2xl font-extrabold font-mono tracking-tight">0 - 1500 V</div>
                <div className={`text-xs mt-1 ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>Full-scale hardware bounds</div>
              </div>
              <div className={`p-4 rounded-xl border ${isDark ? 'bg-[#16181d] border-[#272a31]' : 'bg-white border-slate-200 shadow-sm'}`}>
                <div className="text-xs uppercase font-bold text-emerald-400 mb-1">Current Capability</div>
                <div className="text-2xl font-extrabold font-mono tracking-tight">0 - 1000 A</div>
                <div className={`text-xs mt-1 ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>Constant current & CC limits</div>
              </div>
              <div className={`p-4 rounded-xl border ${isDark ? 'bg-[#16181d] border-[#272a31]' : 'bg-white border-slate-200 shadow-sm'}`}>
                <div className="text-xs uppercase font-bold text-amber-400 mb-1">Power Output</div>
                <div className="text-2xl font-extrabold font-mono tracking-tight">1.2 MW</div>
                <div className={`text-xs mt-1 ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>Parallel stack capability</div>
              </div>
              <div className={`p-4 rounded-xl border ${isDark ? 'bg-[#16181d] border-[#272a31]' : 'bg-white border-slate-200 shadow-sm'}`}>
                <div className="text-xs uppercase font-bold text-purple-400 mb-1">Telemetry Rate</div>
                <div className="text-2xl font-extrabold font-mono tracking-tight">60 FPS</div>
                <div className={`text-xs mt-1 ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>Hardware-accelerated ring buffer</div>
              </div>
            </div>

            {/* Launch Banner */}
            <div id="launch" className={`p-6 rounded-xl border ${isDark ? 'bg-[#16181d] border-[#272a31]' : 'bg-white border-slate-200 shadow-sm'}`}>
              <div className="flex items-start justify-between flex-wrap gap-4">
                <div>
                  <h2 className="text-lg font-bold mb-1 flex items-center gap-2">
                    <Terminal className="w-5 h-5 text-sky-400" />
                    How to Launch the Python Desktop Application
                  </h2>
                  <p className={`text-sm ${isDark ? 'text-slate-400' : 'text-slate-600'}`}>
                    The complete, publication-grade PyQt6 application is implemented in <code className="text-sky-400 font-mono">/labhp_controller_v5.py</code>.
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <span className="px-3 py-1 text-xs rounded-full bg-emerald-500/10 text-emerald-400 font-semibold border border-emerald-500/20">
                    ● Syntax Verified OK
                  </span>
                </div>
              </div>

              <div className={`mt-4 p-3 rounded-lg font-mono text-sm border overflow-x-auto ${isDark ? 'bg-[#0f1115] border-[#272a31] text-sky-300' : 'bg-slate-100 border-slate-300 text-sky-800'}`}>
                python3 labhp_controller_v5.py
              </div>
            </div>
          </div>
        )}

        {/* Tab 2: Export & Customization */}
        {activeTab === 'export' && (
          <div className="space-y-6">
            <div className={`p-6 rounded-xl border ${isDark ? 'bg-[#16181d] border-[#272a31]' : 'bg-white border-slate-200 shadow-sm'}`}>
              <h2 className="text-lg font-bold mb-3 flex items-center gap-2">
                <Download className="w-5 h-5 text-sky-400" />
                Multi-Format Export Engine
              </h2>
              <p className={`text-sm mb-6 ${isDark ? 'text-slate-400' : 'text-slate-600'}`}>
                Both live oscilloscope telemetry waveforms and historical session CSV logs support 4 high-resolution publication formats:
              </p>

              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
                <div className={`p-4 rounded-lg border ${isDark ? 'bg-[#1f232b] border-[#2e3340]' : 'bg-slate-50 border-slate-200'}`}>
                  <span className="font-bold text-sky-400 block mb-1">PDF (.pdf)</span>
                  <p className="text-xs text-slate-400">Crisp vector documents at 300/600 DPI, styled for journal and lab test reports.</p>
                </div>
                <div className={`p-4 rounded-lg border ${isDark ? 'bg-[#1f232b] border-[#2e3340]' : 'bg-slate-50 border-slate-200'}`}>
                  <span className="font-bold text-emerald-400 block mb-1">PNG (.png)</span>
                  <p className="text-xs text-slate-400">High-resolution lossless raster renderings with customized titles, axes, and line weights.</p>
                </div>
                <div className={`p-4 rounded-lg border ${isDark ? 'bg-[#1f232b] border-[#2e3340]' : 'bg-slate-50 border-slate-200'}`}>
                  <span className="font-bold text-amber-400 block mb-1">JPEG (.jpg, .jpeg)</span>
                  <p className="text-xs text-slate-400">RGB888 solid background images with 95% quality for presentations and web reports.</p>
                </div>
                <div className={`p-4 rounded-lg border ${isDark ? 'bg-[#1f232b] border-[#2e3340]' : 'bg-slate-50 border-slate-200'}`}>
                  <span className="font-bold text-purple-400 block mb-1">SVG (.svg)</span>
                  <p className="text-xs text-slate-400">Scalable vector graphics via Matplotlib and QSvgGenerator for infinite zoom without blur.</p>
                </div>
              </div>
            </div>

            {/* Customization Details */}
            <div className={`p-6 rounded-xl border ${isDark ? 'bg-[#16181d] border-[#272a31]' : 'bg-white border-slate-200 shadow-sm'}`}>
              <h3 className="text-base font-bold mb-4 flex items-center gap-2">
                <Settings2 className="w-5 h-5 text-sky-400" />
                Plot Presentation Customization Dialog (⚙ Settings...)
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                <div className={`p-3 rounded-lg border ${isDark ? 'bg-[#1f232b] border-[#2e3340]' : 'bg-slate-50 border-slate-200'}`}>
                  <strong className="text-sky-400">X and Y Axis Customization:</strong>
                  <p className="text-xs mt-1 text-slate-400">Edit titles (e.g. "Elapsed Time", "Process Variable") and engineering units ("s", "min", "V", "A", "W"). Reflects in UI and exports.</p>
                </div>
                <div className={`p-3 rounded-lg border ${isDark ? 'bg-[#1f232b] border-[#2e3340]' : 'bg-slate-50 border-slate-200'}`}>
                  <strong className="text-emerald-400">Legend Position Control:</strong>
                  <p className="text-xs mt-1 text-slate-400">6 flexible anchors: Top-Right, Top-Left, Bottom-Right, Bottom-Left, Top-Center, Bottom-Center, or Hidden to avoid overlapping active waveforms.</p>
                </div>
                <div className={`p-3 rounded-lg border ${isDark ? 'bg-[#1f232b] border-[#2e3340]' : 'bg-slate-50 border-slate-200'}`}>
                  <strong className="text-amber-400">Title & Alignment:</strong>
                  <p className="text-xs mt-1 text-slate-400">Custom chart header with Left, Center, or Right alignment and toggleable visibility.</p>
                </div>
                <div className={`p-3 rounded-lg border ${isDark ? 'bg-[#1f232b] border-[#2e3340]' : 'bg-slate-50 border-slate-200'}`}>
                  <strong className="text-purple-400">Trace Width, Grids & Theme:</strong>
                  <p className="text-xs mt-1 text-slate-400">Configurable 1.0–3.0 px pen thickness, X/Y grid filters, and selectable export theme (Dark, Light, or GUI sync).</p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Tab 3: Themes */}
        {activeTab === 'features' && (
          <div className="space-y-6">
            <div className={`p-6 rounded-xl border ${isDark ? 'bg-[#16181d] border-[#272a31]' : 'bg-white border-slate-200 shadow-sm'}`}>
              <h2 className="text-lg font-bold mb-3 flex items-center gap-2">
                <Sun className="w-5 h-5 text-amber-400" />
                Adaptive Dark & Light Theme System
              </h2>
              <p className={`text-sm mb-4 ${isDark ? 'text-slate-400' : 'text-slate-600'}`}>
                Designed according to ergonomic industrial UI best practices:
              </p>
              <ul className="space-y-3 text-sm">
                <li className="flex items-start gap-2">
                  <div className="w-2 h-2 rounded-full bg-sky-400 mt-2 shrink-0"></div>
                  <div>
                    <strong className="text-sky-400">Dark Mode (Default):</strong> High-contrast Slate theme (<code className="font-mono text-xs">#0f1115</code> base canvas, <code className="font-mono text-xs">#16181d</code> cards) with subdued saturated accents to minimize eye fatigue during extended bench sessions.
                  </div>
                </li>
                <li className="flex items-start gap-2">
                  <div className="w-2 h-2 rounded-full bg-amber-400 mt-2 shrink-0"></div>
                  <div>
                    <strong className="text-amber-400">Light Mode (Clean Lab Cleanroom):</strong> High-legibility paper-like surface (<code className="font-mono text-xs">#f8fafc</code> canvas, <code className="font-mono text-xs">#ffffff</code> cards) with WCAG AA-compliant typography and high-contrast waveforms.
                  </div>
                </li>
                <li className="flex items-start gap-2">
                  <div className="w-2 h-2 rounded-full bg-emerald-400 mt-2 shrink-0"></div>
                  <div>
                    <strong className="text-emerald-400">Seamless Synchronization:</strong> Toggle button in the header bar updates the entire application hierarchy, metric cards, status badges, and plot canvases dynamically.
                  </div>
                </li>
              </ul>
            </div>
          </div>
        )}

        {/* Tab 4: Code Preview */}
        {activeTab === 'code' && (
          <div className={`p-6 rounded-xl border font-mono text-xs overflow-x-auto ${isDark ? 'bg-[#121418] border-[#272a31] text-slate-300' : 'bg-slate-900 border-slate-800 text-slate-200'}`}>
            <div className="flex items-center justify-between pb-3 mb-3 border-b border-slate-700">
              <span className="text-sky-400 font-bold">labhp_controller_v5.py — Key Architecture</span>
              <span className="text-slate-400">Python 3.10+ / PyQt6</span>
            </div>
            <pre className="leading-relaxed">
{`# -----------------------------------------------------------------------------
# LAB-HP CONTROLLER v5.0 - PRODUCTION CAPABILITIES SUMMARY
# -----------------------------------------------------------------------------
# 1. Full-Session Historical Log Plotter in Tab 2 (Auto-bind on stop or manual CSV load)
# 2. Multi-Format Export Engine: PDF, PNG, JPEG, SVG across both Live and Historical plots
# 3. Plot Presentation Settings Dialog (Title, Alignment, X/Y Labels, Unit, Legend Location)
# 4. Global Dark Mode & Light Mode Theme Support (Persisted across sessions via QSettings)
# 5. Publication-grade vector outputs via Matplotlib / PyQtGraph / QSvgGenerator at 300+ DPI`}
            </pre>
          </div>
        )}
      </main>
    </div>
  );
}
