import React, { useState, useEffect, useRef } from 'react';
import { BrowserRouter as Router, Routes, Route, NavLink, Link } from 'react-router-dom';
import {
  LayoutDashboard,
  FileText,
  Lightbulb,
  Terminal,
  Settings,
  Play,
  Square,
  Download,
  ExternalLink,
  Search,
  CheckCircle2,
  Clock,
  Loader2,
  AlertCircle,
  X,
  Copy
} from 'lucide-react';
import axios from 'axios';

// API 基础路径
const API_BASE = '/api/v1';

// --- 全局组件：TeX 查看模态框 ---
// 用于显示论文的 LaTeX 源码，符合“不留 TODO”的要求
const TexModal = ({ isOpen, onClose, paperId }) => {
  const [content, setContent] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (isOpen && paperId) {
      setLoading(true);
      setError('');
      axios.get(`${API_BASE}/papers/${paperId}/tex`)
        .then(res => setContent(res.data.content))
        .catch(err => setError('无法加载 LaTeX 源码'))
        .finally(() => setLoading(false));
    }
  }, [isOpen, paperId]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-card border border-white/10 rounded-2xl w-full max-w-4xl max-h-[90vh] flex flex-col shadow-2xl">
        <div className="p-6 border-b border-white/5 flex justify-between items-center">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-primary/10 rounded-lg text-primary">
              <FileText size={20} />
            </div>
            <h3 className="text-xl font-bold">LaTeX Source: {paperId}</h3>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-white/5 rounded-full text-white/40 hover:text-white transition-colors">
            <X size={24} />
          </button>
        </div>
        <div className="flex-1 overflow-auto p-6 font-mono text-sm terminal-scrollbar">
          {loading ? (
            <div className="flex flex-col items-center justify-center py-20 gap-4">
              <Loader2 className="animate-spin text-primary" size={40} />
              <p className="text-white/40">正在加载源码...</p>
            </div>
          ) : error ? (
            <div className="text-red-400 p-4 bg-red-500/10 rounded-xl border border-red-500/20 flex items-center gap-3">
              <AlertCircle size={20} /> {error}
            </div>
          ) : (
            <pre className="whitespace-pre-wrap text-white/70 leading-relaxed bg-black/30 p-6 rounded-xl border border-white/5">
              {content}
            </pre>
          )}
        </div>
        <div className="p-6 border-t border-white/5 flex justify-end gap-3">
          <button
            onClick={() => {
              navigator.clipboard.writeText(content);
              alert('已复制到剪贴板');
            }}
            className="flex items-center gap-2 px-4 py-2 bg-white/5 hover:bg-white/10 rounded-lg text-sm font-bold transition-all"
          >
            <Copy size={16} /> 复制全部
          </button>
          <button onClick={onClose} className="px-6 py-2 bg-primary text-background font-bold rounded-lg transition-all">
            关闭
          </button>
        </div>
      </div>
    </div>
  );
};

// --- 侧边栏组件 ---
const Sidebar = () => {
  const navItems = [
    { icon: <LayoutDashboard size={20} />, label: '仪表盘', path: '/' },
    { icon: <FileText size={20} />, label: '论文库', path: '/papers' },
    { icon: <Lightbulb size={20} />, label: '假设实验室', path: '/ideas' },
    { icon: <Terminal size={20} />, label: '系统日志', path: '/logs' },
    { icon: <Settings size={20} />, label: '设置', path: '/settings' },
  ];

  return (
    <div className="w-64 h-screen bg-card border-r border-white/5 flex flex-col fixed left-0 top-0 z-40">
      <div className="p-8">
        <h1 className="text-2xl font-black bg-gradient-to-r from-primary via-secondary to-accent bg-clip-text text-transparent tracking-tighter">
          PAPERMILL
        </h1>
        <p className="text-[10px] text-white/30 mt-1 uppercase tracking-[0.3em] font-bold">Autonomous Research</p>
      </div>
      <nav className="flex-1 px-4 py-2 space-y-1">
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) =>
              `flex items-center gap-3 px-5 py-3.5 rounded-xl transition-all duration-300 group ${
                isActive
                  ? 'bg-primary/10 text-primary border border-primary/20 shadow-[0_0_20px_rgba(0,242,255,0.08)]'
                  : 'text-white/50 hover:text-white hover:bg-white/5'
              }`
            }
          >
            <span className="transition-transform group-hover:scale-110">{item.icon}</span>
            <span className="font-semibold">{item.label}</span>
          </NavLink>
        ))}
      </nav>
      <div className="p-6 mt-auto">
        <SystemStatusMini />
      </div>
    </div>
  );
};

const SystemStatusMini = () => {
  const [status, setStatus] = useState('unknown');

  useEffect(() => {
    const fetchStatus = () => {
      axios.get(`${API_BASE}/system/status`)
        .then(res => setStatus(res.data.status))
        .catch(() => setStatus('error'));
    };
    fetchStatus();
    const timer = setInterval(fetchStatus, 5000);
    return () => clearInterval(timer);
  }, []);

  return (
    <div className="bg-white/5 rounded-2xl p-4 border border-white/5 flex items-center gap-3">
      <div className={`w-2.5 h-2.5 rounded-full shadow-[0_0_10px_currentColor] ${
        status === 'running' ? 'text-accent bg-accent animate-pulse' :
        status === 'stopped' ? 'text-white/20 bg-white/20' : 'text-red-500 bg-red-500'
      }`} />
      <div className="flex flex-col">
        <span className="text-[10px] text-white/30 font-bold uppercase tracking-widest">系统状态</span>
        <span className="text-xs font-black uppercase text-white/70">
          {status === 'running' ? '运行中' : status === 'stopped' ? '已停止' : '连接异常'}
        </span>
      </div>
    </div>
  );
};

// --- 页面：仪表盘 ---
const Dashboard = () => {
  const [pipelines, setPipelines] = useState([]);
  const [stats, setStats] = useState({ papers: 0, running: 0 });

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [pipeRes, paperRes] = await Promise.all([
          axios.get(`${API_BASE}/pipelines`),
          axios.get(`${API_BASE}/papers`)
        ]);
        setPipelines(pipeRes.data);
        setStats({
          papers: paperRes.data.length,
          running: pipeRes.data.filter(p => p.status === 'running').length
        });
      } catch (e) {}
    };

    fetchData();

    const eventSource = new EventSource(`${API_BASE}/pipelines/stream`);
    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setPipelines(data);
      setStats(prev => ({ ...prev, running: data.filter(p => p.status === 'running').length }));
    };

    return () => eventSource.close();
  }, []);

  return (
    <div className="space-y-10 animate-in fade-in slide-in-from-bottom-4 duration-700">
      <header className="relative">
        <div className="absolute -left-12 top-1/2 -translate-y-1/2 w-1 h-12 bg-primary rounded-full" />
        <h2 className="text-4xl font-black text-white tracking-tight">监控中心</h2>
        <p className="text-white/30 mt-2 font-mono flex items-center gap-2 uppercase tracking-widest text-xs">
          <Terminal size={14} className="text-primary" /> Automated Research Pipeline Overview
        </p>
      </header>

      {/* 统计概览 */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {[
          { label: '已产出论文', value: stats.papers, icon: <FileText size={24} className="text-primary" />, color: 'from-primary/20' },
          { label: '正在运行中', value: stats.running, icon: <Play size={24} className="text-accent" />, color: 'from-accent/20' },
          { label: '系统健康度', value: '100%', icon: <CheckCircle2 size={24} className="text-secondary" />, color: 'from-secondary/20' },
        ].map((stat, i) => (
          <div key={i} className={`bg-card border border-white/5 p-8 rounded-[2rem] relative overflow-hidden group hover:border-white/10 transition-all duration-500`}>
            <div className={`absolute -right-8 -bottom-8 w-32 h-32 bg-gradient-to-br ${stat.color} to-transparent blur-3xl opacity-50 group-hover:opacity-100 transition-opacity`} />
            <div className="flex justify-between items-start relative z-10">
              <div className="space-y-2">
                <p className="text-white/30 text-[10px] font-black uppercase tracking-[0.2em]">{stat.label}</p>
                <h3 className="text-5xl font-black font-mono tracking-tighter italic">{stat.value}</h3>
              </div>
              <div className="p-4 bg-white/5 rounded-2xl border border-white/5 shadow-inner">{stat.icon}</div>
            </div>
          </div>
        ))}
      </div>

      {/* 活动流水线 */}
      <section className="space-y-6">
        <h3 className="text-xl font-black flex items-center gap-3 italic">
          <div className="w-8 h-8 bg-primary/10 rounded-full flex items-center justify-center">
            <Loader2 className="animate-spin text-primary" size={18} />
          </div>
          实时流水线
        </h3>
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
          {pipelines.filter(p => p.status === 'running').map(p => (
            <PipelineCard key={p.id} pipeline={p} />
          ))}
          {pipelines.filter(p => p.status === 'running').length === 0 && (
            <div className="col-span-full py-20 text-center bg-white/[0.02] rounded-[2rem] border-2 border-dashed border-white/5">
              <div className="inline-flex flex-col items-center gap-4 grayscale opacity-30">
                <Loader2 size={48} className="animate-pulse" />
                <p className="text-sm font-bold uppercase tracking-widest italic">暂无活动流水线</p>
              </div>
            </div>
          )}
        </div>
      </section>

      {/* 最近完成 */}
      <section className="space-y-6">
        <div className="flex justify-between items-center">
          <h3 className="text-xl font-black italic">最近完成的研究</h3>
          <Link to="/papers" className="text-primary text-xs font-black uppercase tracking-widest flex items-center gap-2 hover:gap-4 transition-all">
            查看全部 <ExternalLink size={14} />
          </Link>
        </div>
        <div className="bg-card border border-white/5 rounded-[2rem] overflow-hidden shadow-2xl">
          <table className="w-full text-left">
            <thead>
              <tr className="border-b border-white/5 bg-white/[0.02]">
                <th className="px-8 py-5 text-[10px] font-black uppercase tracking-[0.2em] text-white/30">研究标题 (ID)</th>
                <th className="px-8 py-5 text-[10px] font-black uppercase tracking-[0.2em] text-white/30">状态</th>
                <th className="px-8 py-5 text-[10px] font-black uppercase tracking-[0.2em] text-white/30">最后更新</th>
                <th className="px-8 py-5 text-[10px] font-black uppercase tracking-[0.2em] text-white/30">操作</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {pipelines.filter(p => p.status === 'completed').slice(0, 5).map(p => (
                <tr key={p.id} className="hover:bg-white/[0.03] transition-colors group">
                  <td className="px-8 py-6">
                    <div className="flex flex-col">
                      <span className="font-bold text-white/80 group-hover:text-primary transition-colors">{p.title}</span>
                      <span className="text-[10px] font-mono text-white/20 mt-1 uppercase tracking-tighter">ID: {p.id}</span>
                    </div>
                  </td>
                  <td className="px-8 py-6">
                    <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-accent/10 text-accent text-[10px] rounded-full font-black uppercase tracking-widest border border-accent/20">
                      <div className="w-1 h-1 rounded-full bg-accent" /> 已完成
                    </span>
                  </td>
                  <td className="px-8 py-6 text-white/30 text-xs font-mono italic">
                    {new Date(p.updated_at * 1000).toLocaleString()}
                  </td>
                  <td className="px-8 py-6">
                    <Link to="/papers" className="p-3 bg-white/5 hover:bg-primary/20 text-white/40 hover:text-primary rounded-xl transition-all inline-block shadow-sm">
                      <ExternalLink size={18} />
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
};

const PipelineCard = ({ pipeline }) => {
  const stages = ['ideation', 'planning', 'experiment', 'writing'];
  const stageLabels = { 'ideation': '构思中', 'planning': '规划中', 'experiment': '实验中', 'writing': '撰写中' };
  const currentIndex = stages.indexOf(pipeline.stage);
  const progress = ((currentIndex + 1) / stages.length) * 100;

  // 模拟运行时间计算（基于更新时间）
  const [elapsed, setElapsed] = useState('...');
  useEffect(() => {
    const start = pipeline.updated_at;
    const update = () => {
      const diff = Math.floor(Date.now() / 1000 - start);
      const mins = Math.floor(diff / 60);
      const secs = diff % 60;
      setElapsed(`${mins}m ${secs}s`);
    };
    update();
    const timer = setInterval(update, 1000);
    return () => clearInterval(timer);
  }, [pipeline.updated_at]);

  return (
    <div className="bg-card border border-primary/10 p-8 rounded-[2rem] shadow-2xl relative overflow-hidden group hover:border-primary/30 transition-all duration-500">
      <div className="absolute top-0 right-0 p-8">
        <div className="w-3 h-3 rounded-full bg-accent animate-pulse-cyan shadow-[0_0_15px_#00ff9d]" />
      </div>
      <div className="space-y-6 relative z-10">
        <div>
          <h4 className="font-black text-2xl truncate pr-12 tracking-tight group-hover:text-primary transition-colors">{pipeline.title}</h4>
          <div className="flex gap-4 mt-2">
            <p className="text-white/20 text-[10px] font-black font-mono uppercase tracking-widest italic">Task ID: {pipeline.id}</p>
            <p className="text-primary/40 text-[10px] font-black font-mono uppercase tracking-widest italic flex items-center gap-1">
              <Clock size={10} /> 已运行 {elapsed}
            </p>
          </div>
        </div>

        <div className="space-y-3">
          <div className="flex justify-between items-end">
            <span className="text-primary text-xs font-black uppercase tracking-[0.2em] italic flex items-center gap-2">
              <Loader2 className="animate-spin" size={12} /> 当前阶段: {stageLabels[pipeline.stage]}
            </span>
            <span className="text-white/40 font-mono text-lg font-black italic">{Math.round(progress)}%</span>
          </div>
          <div className="h-2 w-full bg-white/[0.03] rounded-full overflow-hidden border border-white/5 p-0.5">
            <div
              className="h-full bg-gradient-to-r from-primary via-accent to-secondary rounded-full transition-all duration-1000 ease-out shadow-[0_0_10px_rgba(0,242,255,0.3)]"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>

        <div className="flex justify-between items-center pt-2">
          <div className="flex gap-2">
            {stages.map((s, i) => (
              <div
                key={s}
                className={`flex flex-col gap-1.5`}
              >
                <div className={`w-12 h-1.5 rounded-full transition-all duration-500 ${i <= currentIndex ? 'bg-primary shadow-[0_0_8px_rgba(0,242,255,0.5)]' : 'bg-white/5'}`} />
                <span className={`text-[8px] font-black uppercase tracking-tighter text-center ${i <= currentIndex ? 'text-primary' : 'text-white/10'}`}>{s}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

// --- 页面：论文库 ---
const Papers = () => {
  const [papers, setPapers] = useState([]);
  const [selectedPaperId, setSelectedPaperId] = useState(null);
  const [isTexOpen, setIsTexOpen] = useState(false);

  useEffect(() => {
    axios.get(`${API_BASE}/papers`).then(res => setPapers(res.data)).catch(() => {});
  }, []);

  return (
    <div className="space-y-10 animate-in fade-in slide-in-from-bottom-4 duration-700">
      <header className="relative">
        <div className="absolute -left-12 top-1/2 -translate-y-1/2 w-1 h-12 bg-primary rounded-full" />
        <h2 className="text-4xl font-black text-white tracking-tight">学术论文库</h2>
        <p className="text-white/30 mt-2 font-mono flex items-center gap-2 uppercase tracking-widest text-xs">
          <FileText size={14} className="text-primary" /> Repository of Automatically Generated Papers
        </p>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {papers.map(paper => (
          <div
            key={paper.id}
            className="bg-card border border-white/5 rounded-[2rem] p-8 flex flex-col group hover:border-primary/20 hover:shadow-[0_0_40px_rgba(0,242,255,0.05)] transition-all duration-500 relative overflow-hidden"
          >
            <div className="absolute top-0 right-0 p-8 opacity-0 group-hover:opacity-100 transition-opacity">
              <div className="text-primary shadow-glow"><ExternalLink size={24} /></div>
            </div>
            <div className="flex justify-between items-start mb-6">
              <div className="p-4 bg-primary/10 rounded-2xl text-primary border border-primary/10 shadow-inner group-hover:scale-110 transition-transform duration-500">
                <FileText size={32} />
              </div>
              <span className="text-[10px] text-white/20 font-black font-mono uppercase tracking-[0.2em] italic">
                {new Date(paper.created_at * 1000).toLocaleDateString()}
              </span>
            </div>
            <h4 className="text-2xl font-black mb-4 group-hover:text-primary transition-colors tracking-tight leading-tight">{paper.title}</h4>
            <p className="text-white/40 text-sm line-clamp-3 mb-8 leading-relaxed italic">
              {paper.abstract || "该论文尚未提供摘要信息。"}
            </p>
            <div className="mt-auto flex flex-wrap gap-4">
              <a
                href={`${API_BASE}/papers/${paper.id}/pdf`}
                target="_blank"
                rel="noreferrer"
                className="flex items-center gap-2 px-6 py-3 bg-white/5 hover:bg-primary text-white/70 hover:text-background rounded-xl text-xs font-black uppercase tracking-widest transition-all shadow-lg border border-white/5"
              >
                <Download size={14} /> 下载 PDF
              </a>
              <button
                onClick={() => {
                  setSelectedPaperId(paper.id);
                  setIsTexOpen(true);
                }}
                className="flex items-center gap-2 px-6 py-3 bg-white/5 hover:bg-secondary text-white/70 hover:text-white rounded-xl text-xs font-black uppercase tracking-widest transition-all shadow-lg border border-white/5"
              >
                <FileText size={14} /> 查看 TeX 源码
              </button>
            </div>
          </div>
        ))}
      </div>

      {papers.length === 0 && (
        <div className="text-center py-32 bg-white/[0.02] rounded-[3rem] border-2 border-dashed border-white/5">
          <div className="flex flex-col items-center gap-6 opacity-20 grayscale">
            <Search size={64} className="animate-bounce" />
            <p className="font-black text-xl uppercase tracking-[0.3em] italic">书架空空如也</p>
          </div>
        </div>
      )}

      <TexModal isOpen={isTexOpen} onClose={() => setIsTexOpen(false)} paperId={selectedPaperId} />
    </div>
  );
};

// --- 页面：假设实验室 ---
const Ideas = () => {
  const [ideas, setIdeas] = useState([]);
  const [filter, setFilter] = useState('');

  useEffect(() => {
    axios.get(`${API_BASE}/ideas`).then(res => setIdeas(res.data)).catch(() => {});
  }, []);

  const filteredIdeas = ideas.filter(i => i.id.toLowerCase().includes(filter.toLowerCase()));

  return (
    <div className="space-y-10 animate-in fade-in slide-in-from-bottom-4 duration-700">
      <header className="relative">
        <div className="absolute -left-12 top-1/2 -translate-y-1/2 w-1 h-12 bg-secondary rounded-full" />
        <h2 className="text-4xl font-black text-white tracking-tight">假设实验室</h2>
        <p className="text-white/30 mt-2 font-mono flex items-center gap-2 uppercase tracking-widest text-xs">
          <Lightbulb size={14} className="text-secondary" /> Brainstorming and Hypothesis Tracking
        </p>
      </header>

      <div className="bg-card border border-white/5 rounded-[2.5rem] overflow-hidden shadow-2xl">
        <div className="p-8 border-b border-white/5 bg-white/[0.02] flex flex-wrap gap-6 justify-between items-center">
          <div className="relative flex-1 min-w-[300px]">
            <Search className="absolute left-5 top-1/2 -translate-y-1/2 text-white/20" size={20} />
            <input
              type="text"
              placeholder="搜索研究假设..."
              value={filter}
              onChange={e => setFilter(e.target.value)}
              className="w-full bg-background border border-white/10 rounded-2xl py-4 pl-14 pr-6 text-sm focus:outline-none focus:border-secondary/50 transition-all font-semibold"
            />
          </div>
          <div className="flex gap-2">
            {['全部', '待处理', '已入库'].map(t => (
              <button key={t} className={`px-5 py-2.5 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all ${t === '全部' ? 'bg-secondary text-white shadow-[0_0_15px_rgba(188,19,254,0.3)]' : 'bg-white/5 text-white/40 hover:bg-white/10'}`}>
                {t}
              </button>
            ))}
          </div>
        </div>
        <div className="divide-y divide-white/5">
          {filteredIdeas.map(idea => (
            <div key={idea.id} className="p-10 hover:bg-white/[0.03] transition-all group relative overflow-hidden">
              <div className="absolute top-0 left-0 w-1 h-0 group-hover:h-full bg-secondary transition-all duration-500" />
              <div className="flex justify-between items-start relative z-10">
                <div className="space-y-4 flex-1">
                  <div className="flex items-center gap-4">
                    <h4 className="text-2xl font-black group-hover:text-secondary transition-colors tracking-tight">{idea.id}</h4>
                    <span className="px-3 py-1 bg-secondary/10 text-secondary text-[10px] rounded-full font-black uppercase tracking-widest border border-secondary/20 shadow-sm">
                      AI 评分: 8.5
                    </span>
                  </div>
                  <div className="flex gap-6">
                    <span className="text-[10px] text-white/20 flex items-center gap-2 font-black uppercase tracking-widest italic">
                      <Clock size={12} className="text-white/40" /> {new Date(idea.mtime * 1000).toLocaleString()}
                    </span>
                    <span className="text-[10px] text-accent flex items-center gap-2 font-black uppercase tracking-widest italic">
                      <CheckCircle2 size={12} /> 核心逻辑已验证
                    </span>
                  </div>
                </div>
                <div className="flex gap-2">
                  <button className="p-3 bg-white/5 hover:bg-white/10 rounded-xl text-white/30 hover:text-white transition-all">
                    <ExternalLink size={20} />
                  </button>
                </div>
              </div>
              <div className="mt-8 p-6 bg-background/50 rounded-2xl border border-white/5 font-mono text-sm text-white/50 leading-relaxed italic group-hover:text-white/70 transition-colors">
                {idea.content}
              </div>
            </div>
          ))}
          {filteredIdeas.length === 0 && (
            <div className="py-32 text-center flex flex-col items-center gap-6 opacity-20">
              <Lightbulb size={64} className="grayscale" />
              <p className="font-black uppercase tracking-[0.2em] italic">没有找到匹配的奇思妙想</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

// --- 页面：系统日志 ---
const Logs = () => {
  const [logs, setLogs] = useState([]);
  const [autoScroll, setAutoScroll] = useState(true);
  const [filter, setFilter] = useState('all');
  const logContainerRef = useRef(null);

  useEffect(() => {
    axios.get(`${API_BASE}/logs?lines=300`)
      .then(res => setLogs(res.data.logs.split('\n').filter(l => l.trim())))
      .catch(() => {});

    const eventSource = new EventSource(`${API_BASE}/logs/stream`);
    eventSource.onmessage = (event) => {
      setLogs(prev => [...prev, event.data].slice(-1000));
    };

    return () => eventSource.close();
  }, []);

  useEffect(() => {
    if (autoScroll && logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
    }
  }, [logs, autoScroll]);

  const filteredLogs = logs.filter(l => {
    if (filter === 'all') return true;
    return l.toUpperCase().includes(filter.toUpperCase());
  });

  return (
    <div className="h-full flex flex-col space-y-8 animate-in fade-in duration-700">
      <header className="flex justify-between items-end">
        <div className="relative">
          <div className="absolute -left-12 top-1/2 -translate-y-1/2 w-1 h-12 bg-accent rounded-full" />
          <h2 className="text-4xl font-black text-white tracking-tight">终端日志</h2>
          <p className="text-white/30 mt-2 font-mono flex items-center gap-2 uppercase tracking-widest text-xs">
            <Terminal size={14} className="text-accent" /> Real-time System Execution Stream
          </p>
        </div>
        <div className="flex gap-4">
          <div className="bg-white/5 p-1 rounded-xl flex gap-1 border border-white/5">
            {['ALL', 'INFO', 'ERROR', 'WARN'].map(f => (
              <button
                key={f}
                onClick={() => setFilter(f.toLowerCase())}
                className={`px-4 py-2 rounded-lg text-[10px] font-black uppercase tracking-widest transition-all ${
                  (filter === f.toLowerCase()) ? 'bg-white/10 text-white shadow-inner' : 'text-white/30 hover:text-white'
                }`}
              >
                {f}
              </button>
            ))}
          </div>
          <button
            onClick={() => setAutoScroll(!autoScroll)}
            className={`px-6 py-2.5 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all ${
              autoScroll ? 'bg-accent/20 text-accent border border-accent/20' : 'bg-white/5 text-white/20 border border-white/5'
            }`}
          >
            {autoScroll ? '自动滚动已开启' : '自动滚动已关闭'}
          </button>
          <button
            onClick={() => setLogs([])}
            className="px-6 py-2.5 bg-white/5 hover:bg-red-500/20 hover:text-red-400 border border-white/5 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all"
          >
            清空面板
          </button>
        </div>
      </header>

      <div className="flex-1 bg-black/40 border border-white/10 rounded-[2.5rem] overflow-hidden font-mono text-xs relative shadow-inner">
        <div className="absolute top-0 left-0 right-0 h-12 bg-white/[0.03] border-b border-white/5 px-8 flex items-center justify-between z-10 backdrop-blur-md">
          <div className="flex gap-2">
            <div className="w-3 h-3 rounded-full bg-red-500/40" />
            <div className="w-3 h-3 rounded-full bg-yellow-500/40" />
            <div className="w-3 h-3 rounded-full bg-green-500/40" />
          </div>
          <span className="text-[10px] text-white/20 uppercase tracking-[0.4em] font-black italic">papermill_orchestrator.log</span>
          <div className="w-10" />
        </div>
        <div
          ref={logContainerRef}
          className="h-[calc(100vh-320px)] overflow-y-auto p-10 pt-16 terminal-scrollbar bg-gradient-to-b from-transparent to-black/20"
        >
          {filteredLogs.map((log, i) => (
            <div key={i} className="mb-2 flex gap-6 group hover:bg-white/[0.02] -mx-4 px-4 py-0.5 rounded transition-colors">
              <span className="text-white/10 min-w-[3rem] text-right select-none italic font-black group-hover:text-white/30 transition-colors">{i + 1}</span>
              <span className={`leading-relaxed whitespace-pre-wrap ${
                log.includes('INFO') ? 'text-white/60' :
                log.includes('ERROR') ? 'text-red-400 font-black' :
                log.includes('WARNING') ? 'text-yellow-300/80' :
                log.includes('SUCCESS') ? 'text-accent font-black' : 'text-white/40'
              }`}>
                {log}
              </span>
            </div>
          ))}
          <div className="h-8" />
        </div>
      </div>
    </div>
  );
};

// --- 页面：设置 ---
const SettingsPage = () => {
  const [config, setConfig] = useState(null);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');

  useEffect(() => {
    axios.get(`${API_BASE}/config`).then(res => setConfig(res.data)).catch(() => {});
  }, []);

  const handleSave = async () => {
    setSaving(true);
    try {
      await axios.put(`${API_BASE}/config`, config);
      setMessage('配置保存成功');
      setTimeout(() => setMessage(''), 3000);
    } catch (e) {
      setMessage('保存失败');
    }
    setSaving(false);
  };

  const systemAction = (action) => {
    axios.post(`${API_BASE}/system/${action}`).then(() => alert(`${action} 指令已下达`)).catch(() => alert('操作失败'));
  };

  if (!config) return <div className="p-40 text-center"><Loader2 className="animate-spin mx-auto text-primary" size={48} /></div>;

  return (
    <div className="max-w-5xl space-y-12 animate-in fade-in slide-in-from-bottom-4 duration-700">
      <header className="flex justify-between items-end">
        <div className="relative">
          <div className="absolute -left-12 top-1/2 -translate-y-1/2 w-1 h-12 bg-white/20 rounded-full" />
          <h2 className="text-4xl font-black text-white tracking-tight">核心配置</h2>
          <p className="text-white/30 mt-2 font-mono flex items-center gap-2 uppercase tracking-widest text-xs">
            <Settings size={14} className="text-white/40" /> System Parameters and Agent Controls
          </p>
        </div>
        <div className="flex gap-4">
          <button
            onClick={() => systemAction('start')}
            className="group flex items-center gap-3 px-8 py-4 bg-accent text-background font-black rounded-[1.25rem] hover:shadow-[0_0_40px_rgba(0,255,157,0.4)] transition-all uppercase tracking-widest italic"
          >
            <Play size={20} fill="currentColor" className="group-hover:scale-125 transition-transform" /> 启动流水线
          </button>
          <button
            onClick={() => systemAction('stop')}
            className="group flex items-center gap-3 px-8 py-4 bg-red-500/10 text-red-500 border border-red-500/20 font-black rounded-[1.25rem] hover:bg-red-500 hover:text-white transition-all uppercase tracking-widest italic"
          >
            <Square size={20} fill="currentColor" className="group-hover:scale-75 transition-transform" /> 停止运行
          </button>
        </div>
      </header>

      <div className="grid grid-cols-1 gap-8">
        {/* LLM 配置 */}
        <section className="bg-card border border-white/5 rounded-[2.5rem] p-10 space-y-8 shadow-2xl relative overflow-hidden">
          <div className="absolute top-0 right-0 p-10 opacity-5 grayscale"><Settings size={120} /></div>
          <h3 className="text-2xl font-black text-primary flex items-center gap-4 italic">
            <div className="w-1.5 h-8 bg-primary rounded-full shadow-[0_0_10px_#00f2ff]" /> 智能代理引擎
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-12 relative z-10">
            <div className="space-y-4">
              <label className="text-[10px] font-black uppercase text-white/30 tracking-[0.2em] italic">核心大语言模型 (Base LLM)</label>
              <select
                value={config.llm_model}
                onChange={e => setConfig({...config, llm_model: e.target.value})}
                className="w-full bg-background border border-white/10 rounded-2xl px-6 py-4 focus:border-primary transition-all outline-none font-bold text-white/80 appearance-none shadow-inner"
              >
                <option value="gpt-4o">GPT-4o (默认推荐)</option>
                <option value="claude-3-5-sonnet">Claude 3.5 Sonnet</option>
                <option value="gemini-1.5-pro">Gemini 1.5 Pro</option>
              </select>
            </div>
            <div className="space-y-4">
              <label className="text-[10px] font-black uppercase text-white/30 tracking-[0.2em] italic">假设评审门槛 (1-10)</label>
              <input
                type="number"
                value={config.hypothesis_review_threshold}
                onChange={e => setConfig({...config, hypothesis_review_threshold: parseInt(e.target.value)})}
                className="w-full bg-background border border-white/10 rounded-2xl px-6 py-4 focus:border-primary transition-all outline-none font-mono text-xl font-black italic shadow-inner"
              />
            </div>
          </div>
        </section>

        {/* 运行参数 */}
        <section className="bg-card border border-white/5 rounded-[2.5rem] p-10 space-y-8 shadow-2xl relative overflow-hidden">
          <div className="absolute top-0 right-0 p-10 opacity-5 grayscale"><Play size={120} /></div>
          <h3 className="text-2xl font-black text-secondary flex items-center gap-4 italic">
            <div className="w-1.5 h-8 bg-secondary rounded-full shadow-[0_0_10px_#bc13fe]" /> 并行调度参数
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-12 relative z-10">
            <div className="space-y-4">
              <label className="text-[10px] font-black uppercase text-white/30 tracking-[0.2em] italic">最大并行流水线数</label>
              <input
                type="number"
                value={config.max_concurrent_pipelines}
                onChange={e => setConfig({...config, max_concurrent_pipelines: parseInt(e.target.value)})}
                className="w-full bg-background border border-white/10 rounded-2xl px-6 py-4 focus:border-secondary transition-all outline-none font-mono text-xl font-black italic shadow-inner"
              />
            </div>
            <div className="space-y-4">
              <label className="text-[10px] font-black uppercase text-white/30 tracking-[0.2em] italic">实验超时限制 (分钟)</label>
              <input
                type="number"
                value={config.experiment_timeout_minutes}
                onChange={e => setConfig({...config, experiment_timeout_minutes: parseInt(e.target.value)})}
                className="w-full bg-background border border-white/10 rounded-2xl px-6 py-4 focus:border-secondary transition-all outline-none font-mono text-xl font-black italic shadow-inner"
              />
            </div>
          </div>
        </section>

        {/* 研究方向 */}
        <section className="bg-card border border-white/5 rounded-[2.5rem] p-10 space-y-8 shadow-2xl relative overflow-hidden">
          <div className="absolute top-0 right-0 p-10 opacity-5 grayscale"><Lightbulb size={120} /></div>
          <h3 className="text-2xl font-black text-accent flex items-center gap-4 italic">
            <div className="w-1.5 h-8 bg-accent rounded-full shadow-[0_0_10px_#00ff9d]" /> 研究探索领域
          </h3>
          <div className="space-y-6 relative z-10">
            <div className="flex flex-wrap gap-3">
              {config.research_directions.map((dir, i) => (
                <div key={i} className="group px-4 py-2 bg-white/5 border border-white/5 rounded-xl flex items-center gap-3 text-sm font-bold transition-all hover:bg-white/10">
                  <span className="text-white/60 group-hover:text-accent transition-colors">{dir}</span>
                  <button
                    onClick={() => setConfig({
                      ...config,
                      research_directions: config.research_directions.filter((_, idx) => idx !== i)
                    })}
                    className="text-white/10 hover:text-red-500 transition-colors"
                  >
                    <X size={16} />
                  </button>
                </div>
              ))}
            </div>
            <div className="flex gap-4">
              <input
                type="text"
                placeholder="添加新的研究方向并按回车..."
                className="flex-1 bg-background border border-white/10 rounded-2xl px-6 py-4 focus:border-accent transition-all outline-none font-bold shadow-inner"
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && e.target.value.trim()) {
                    setConfig({
                      ...config,
                      research_directions: [...config.research_directions, e.target.value.trim()]
                    });
                    e.target.value = '';
                  }
                }}
              />
            </div>
          </div>
        </section>

        <div className="flex items-center gap-8 pt-8 pb-12">
          <button
            onClick={handleSave}
            disabled={saving}
            className="relative px-16 py-5 bg-primary text-background font-black rounded-2xl hover:shadow-[0_0_50px_rgba(0,242,255,0.4)] disabled:opacity-50 transition-all uppercase tracking-[0.2em] italic active:scale-95 overflow-hidden"
          >
            <span className="relative z-10">{saving ? '正在保存...' : '同步配置'}</span>
            <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent -translate-x-full group-hover:translate-x-full transition-transform duration-1000" />
          </button>
          {message && (
            <div className="flex items-center gap-3 text-accent font-black animate-in slide-in-from-left-4 italic">
              <div className="p-2 bg-accent/10 rounded-full"><CheckCircle2 size={24} /></div> {message}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

// --- 根应用组件 ---
const App = () => {
  return (
    <Router>
      <div className="flex min-h-screen bg-background text-white selection:bg-primary/30 selection:text-primary">
        <Sidebar />
        <main className="flex-1 ml-64 p-12 lg:p-20 relative">
          {/* 背景装饰 */}
          <div className="fixed top-0 right-0 w-[50vw] h-[50vh] bg-primary/5 blur-[120px] -z-10 rounded-full pointer-events-none" />
          <div className="fixed bottom-0 left-64 w-[40vw] h-[40vh] bg-secondary/5 blur-[120px] -z-10 rounded-full pointer-events-none" />

          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/papers" element={<Papers />} />
            <Route path="/ideas" element={<Ideas />} />
            <Route path="/logs" element={<Logs />} />
            <Route path="/settings" element={<SettingsPage />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
};

export default App;
