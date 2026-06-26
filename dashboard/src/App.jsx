import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  Activity,
  AlertTriangle,
  ArrowDown,
  ArrowLeft,
  ArrowRight,
  ArrowUp,
  BatteryCharging,
  Cpu,
  Crosshair,
  StopCircle,
  TerminalSquare,
  WifiHigh,
} from 'lucide-react';

const ESC_STOP_PWM = 1500;
const ESC_MIN_MOVE_PWM = 1580;
const ESC_MAX_UI_PWM = 1800;
const SERVO_RIGHT_PWM = 1000;
const SERVO_CENTER_PWM = 1500;
const SERVO_LEFT_PWM = 2000;

function pwmFromSpeedLimit(speedLimit) {
  if (speedLimit <= 0) return ESC_STOP_PWM;
  return Math.round(ESC_MIN_MOVE_PWM + ((ESC_MAX_UI_PWM - ESC_MIN_MOVE_PWM) * speedLimit) / 100);
}

export default function App() {
  const [status, setStatus] = useState('Standby');
  const [speedLimit, setSpeedLimit] = useState(60);
  const [currentSpeed, setCurrentSpeed] = useState(0);
  const [battery, setBattery] = useState(0);
  const [latencyMs, setLatencyMs] = useState('--');
  const [connected, setConnected] = useState(false);
  const [cameraFrame, setCameraFrame] = useState('/api/camera/stream');
  const [logs, setLogs] = useState([
    { time: new Date().toLocaleTimeString(), msg: 'DASHBOARD INICIADA. CONECTANDO AO BACKEND SERIAL.' },
  ]);

  const speedInterval = useRef(null);
  const stopTimer = useRef(null);

  const addLog = (msg) => {
    setLogs((prev) => [{ time: new Date().toLocaleTimeString(), msg }, ...prev].slice(0, 20));
  };

  const applyBackendStatus = (backendStatus, latency) => {
    setConnected(Boolean(backendStatus.connected));
    setLatencyMs(latency);
    setBattery(backendStatus.connected ? 100 : 0);
    setCurrentSpeed(Math.max(0, Number(backendStatus.esc_pwm ?? ESC_STOP_PWM) - ESC_STOP_PWM));
  };

  const api = async (path, options = {}) => {
    const startedAt = performance.now();
    const response = await fetch(path, {
      headers: { 'Content-Type': 'application/json' },
      ...options,
    });
    const latency = Math.round(performance.now() - startedAt);
    const payload = await response.json();
    if (payload.status) applyBackendStatus(payload.status, latency);
    if (!response.ok || !payload.ok) {
      throw new Error(payload.error || 'BACKEND_SERIAL_INDISPONIVEL');
    }
    return payload;
  };

  const refreshStatus = async (silent = false) => {
    try {
      await api('/api/status');
    } catch (error) {
      setConnected(false);
      setLatencyMs('--');
      setBattery(0);
      if (!silent) addLog(`SERIAL_ERRO: ${error.message}`);
    }
  };

  useEffect(() => {
    refreshStatus();
    const statusTimer = setInterval(() => refreshStatus(true), 2500);
    return () => clearInterval(statusTimer);
  }, []);

  const sendPwm = async (channel, value) => {
    try {
      await api('/api/command', {
        method: 'POST',
        body: JSON.stringify({ channel, value }),
      });
      addLog(`PWM_${channel.toUpperCase()}: ${value}`);
    } catch (error) {
      addLog(`SERIAL_ERRO: ${error.message}`);
    }
  };

  const commandForDirection = useMemo(
    () => ({
      Frente: { esc: pwmFromSpeedLimit(speedLimit), servo: SERVO_CENTER_PWM },
      Trás: { esc: ESC_STOP_PWM, servo: SERVO_CENTER_PWM },
      Esquerda: { servo: SERVO_LEFT_PWM },
      Direita: { servo: SERVO_RIGHT_PWM },
    }),
    [speedLimit],
  );

  const handleMove = (direction) => {
    const command = commandForDirection[direction];
    if (!command) return;

    setStatus(direction);
    addLog(`CMD_MOVE: ${direction.toUpperCase()}`);
    if (command.servo) sendPwm('servo', command.servo);
    if (command.esc) sendPwm('esc', command.esc);

    clearInterval(speedInterval.current);
    clearInterval(stopTimer.current);
    speedInterval.current = setInterval(() => {
      if (command.servo) sendPwm('servo', command.servo);
      if (command.esc) sendPwm('esc', command.esc);
    }, 250);
  };

  const handleStop = async () => {
    setStatus('Standby');
    addLog('CMD_STOP: E1500 S1500 enviado');
    clearInterval(speedInterval.current);
    clearInterval(stopTimer.current);
    try {
      await api('/api/stop', { method: 'POST', body: '{}' });
    } catch (error) {
      addLog(`SERIAL_ERRO: ${error.message}`);
    }
    stopTimer.current = setInterval(() => {
      api('/api/stop', { method: 'POST', body: '{}' }).catch((error) => addLog(`SERIAL_ERRO: ${error.message}`));
    }, 250);
    setTimeout(() => clearInterval(stopTimer.current), 400);
  };

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.repeat) return;
      switch (e.key) {
        case 'ArrowUp':
        case 'w':
        case 'W':
          handleMove('Frente');
          break;
        case 'ArrowDown':
        case 's':
        case 'S':
          handleMove('Trás');
          break;
        case 'ArrowLeft':
        case 'a':
        case 'A':
          handleMove('Esquerda');
          break;
        case 'ArrowRight':
        case 'd':
        case 'D':
          handleMove('Direita');
          break;
        case ' ':
          handleStop();
          break;
        default:
          break;
      }
    };

    const handleKeyUp = (e) => {
      const keys = ['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'w', 'W', 'a', 'A', 's', 'S', 'd', 'D'];
      if (keys.includes(e.key)) handleStop();
    };

    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('keyup', handleKeyUp);

    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('keyup', handleKeyUp);
      clearInterval(speedInterval.current);
      clearInterval(stopTimer.current);
    };
  }, [connected, commandForDirection]);

  const ControlButton = ({ icon: Icon, direction }) => {
    const isActive = status === direction;
    return (
      <button
        type="button"
        onMouseDown={() => handleMove(direction)}
        onMouseUp={handleStop}
        onMouseLeave={handleStop}
        onTouchStart={(e) => {
          e.preventDefault();
          handleMove(direction);
        }}
        onTouchEnd={(e) => {
          e.preventDefault();
          handleStop();
        }}
        className={`relative group flex items-center justify-center w-16 h-16 sm:w-20 sm:h-20 rounded-lg transition-all duration-200 select-none touch-none ${
          isActive
            ? 'bg-cyan-500/20 border-cyan-400 text-cyan-300 shadow-[0_0_20px_rgba(34,211,238,0.4)] scale-95'
            : 'bg-white/5 border-white/10 text-slate-400 hover:bg-white/10 hover:text-white hover:border-white/20 shadow-lg'
        } border backdrop-blur-sm`}
        disabled={!connected}
        title={direction}
      >
        <Icon size={32} strokeWidth={isActive ? 2.5 : 1.5} className="relative z-10" />
      </button>
    );
  };

  const strokeDasharray = 251.2;
  const strokeDashoffset = strokeDasharray - (strokeDasharray * Math.min(currentSpeed, 100)) / 100;

  return (
    <div className="min-h-screen bg-[#050505] text-slate-200 font-sans selection:bg-cyan-500/30 relative overflow-x-hidden">
      <div className="fixed inset-0 bg-[linear-gradient(to_right,#8080800a_1px,transparent_1px),linear-gradient(to_bottom,#8080800a_1px,transparent_1px)] bg-[size:40px_40px] pointer-events-none" />

      <div className="max-w-7xl mx-auto p-3 sm:p-4 md:p-8 space-y-4 md:space-y-6 relative z-10">
        <header className="flex flex-col md:flex-row items-center justify-between bg-white/[0.03] backdrop-blur-xl p-4 sm:p-5 rounded-lg border border-white/10 shadow-2xl gap-4">
          <div className="flex items-center gap-3 sm:gap-4">
            <div className="p-2 sm:p-3 bg-gradient-to-br from-cyan-500 to-blue-600 rounded-lg shadow-[0_0_15px_rgba(34,211,238,0.3)] flex items-center justify-center shrink-0">
              <Cpu className="text-white" size={24} />
            </div>
            <div>
              <h1 className="text-xl sm:text-2xl font-black tracking-wider text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-indigo-400">
                CARRINHO<span className="text-white">RC</span>
              </h1>
              <p className="text-cyan-500/60 text-[10px] sm:text-xs font-mono tracking-widest uppercase truncate">Serial Control Unit</p>
            </div>
          </div>

          <div className="flex flex-wrap justify-center gap-3 sm:gap-4 font-mono text-xs sm:text-sm">
            <div className="flex items-center gap-2 px-3 sm:px-4 py-2 bg-black/40 rounded-full border border-white/5">
              <span className="relative flex h-2.5 w-2.5 sm:h-3 sm:w-3">
                {connected && <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />}
                <span className={`relative inline-flex rounded-full h-2.5 w-2.5 sm:h-3 sm:w-3 ${connected ? 'bg-emerald-500' : 'bg-red-500'}`} />
              </span>
              <WifiHigh className={connected ? 'text-emerald-500' : 'text-red-500'} size={14} />
              <span className="text-slate-300 tracking-wider">{latencyMs}ms</span>
            </div>
            <div className="flex items-center gap-2 px-3 sm:px-4 py-2 bg-black/40 rounded-full border border-white/5">
              <BatteryCharging className="text-cyan-400" size={16} />
              <span className="text-slate-300 font-bold">{battery}%</span>
            </div>
          </div>
        </header>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 md:gap-6">
          <div className="lg:col-span-8 order-1">
            <div className="relative w-full aspect-video bg-black rounded-lg border border-white/10 overflow-hidden shadow-2xl shadow-black/50 flex items-center justify-center group">
              {cameraFrame ? (
                <img
                  src={cameraFrame}
                  alt="Camera frontal"
                  className="absolute inset-0 h-full w-full object-cover"
                  onError={() => setCameraFrame('')}
                />
              ) : (
                <div className="text-center z-0 opacity-30">
                  <Activity size={48} className="mx-auto mb-2 sm:mb-4 text-cyan-500 animate-pulse sm:w-[64px] sm:h-[64px]" />
                  <p className="font-mono text-[10px] sm:text-sm tracking-widest text-cyan-500">AGUARDANDO VIDEO</p>
                </div>
              )}

              <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0),rgba(255,255,255,0)_50%,rgba(0,0,0,0.2)_50%,rgba(0,0,0,0.2))] bg-[length:100%_4px] pointer-events-none z-10 opacity-30" />
              <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,transparent_50%,rgba(0,0,0,0.65)_100%)] pointer-events-none z-10" />

              <div className="absolute top-4 sm:top-6 left-4 sm:left-6 z-20 flex flex-col gap-2">
                <div className="px-2 sm:px-3 py-1 bg-red-500/20 border border-red-500/50 backdrop-blur-md rounded-md flex items-center gap-1.5 sm:gap-2 self-start">
                  <div className="w-2 h-2 sm:w-2.5 sm:h-2.5 bg-red-500 rounded-full animate-pulse shadow-[0_0_8px_rgba(239,68,68,0.8)]" />
                  <span className="text-red-400 font-mono text-[10px] sm:text-xs font-bold tracking-widest">REC</span>
                </div>
                <span className="text-white/50 font-mono text-[8px] sm:text-xs">CAM_FRONTAL_01</span>
              </div>

              <div className="absolute top-4 sm:top-6 right-4 sm:right-6 z-20 text-right font-mono text-[8px] sm:text-xs text-cyan-400/70 space-y-0.5 sm:space-y-1">
                <p>USB: {connected ? 'ONLINE' : 'OFFLINE'}</p>
                <p>PROTOCOLO: E/S PWM</p>
              </div>

              <div className="absolute inset-0 flex items-center justify-center pointer-events-none z-20 overflow-hidden">
                <Crosshair size={80} strokeWidth={1} className="text-cyan-500/30 sm:w-[120px] sm:h-[120px]" />
                <div className="absolute w-40 h-40 sm:w-64 sm:h-64 border border-cyan-500/20 rounded-full border-dashed animate-[spin_30s_linear_infinite]" />
                <div className="absolute w-56 h-56 sm:w-80 sm:h-80 border-t border-b border-cyan-500/10 rounded-full animate-[spin_20s_linear_infinite_reverse]" />
              </div>
            </div>
          </div>

          <div className="lg:col-span-4 lg:row-span-2 order-2 flex flex-col gap-4 md:gap-6">
            <div className="bg-white/[0.03] backdrop-blur-xl p-5 sm:p-6 rounded-lg border border-white/10 shadow-2xl flex flex-col items-center justify-center relative overflow-hidden">
              <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-cyan-500 to-transparent opacity-50" />

              <div className="flex justify-between items-center w-full mb-4 sm:mb-6">
                <h3 className="text-[10px] sm:text-xs font-bold text-slate-400 tracking-widest uppercase">Velocidade Atual</h3>
                <div className="px-2 py-1 bg-black/40 border border-white/10 rounded-full flex items-center gap-2">
                  <div className={`w-1.5 h-1.5 rounded-full ${status === 'Standby' ? 'bg-amber-500' : 'bg-cyan-400 animate-pulse shadow-[0_0_8px_rgba(34,211,238,0.8)]'}`} />
                  <span className="text-[8px] sm:text-[10px] font-mono font-bold tracking-widest text-slate-300 uppercase">{status}</span>
                </div>
              </div>

              <div className="relative flex items-center justify-center w-36 h-36 sm:w-48 sm:h-48">
                <svg className="w-full h-full transform -rotate-90" viewBox="0 0 100 100">
                  <circle cx="50" cy="50" r="40" stroke="currentColor" strokeWidth="8" fill="transparent" className="text-white/5" />
                  <circle cx="50" cy="50" r="40" stroke="currentColor" strokeWidth="8" fill="transparent" strokeLinecap="round" className="text-cyan-400 drop-shadow-[0_0_10px_rgba(34,211,238,0.8)] transition-all duration-300 ease-out" strokeDasharray={strokeDasharray} strokeDashoffset={strokeDashoffset} />
                </svg>
                <div className="absolute flex flex-col items-center justify-center">
                  <span className="text-4xl sm:text-5xl font-black tracking-normal text-white font-mono drop-shadow-[0_0_10px_rgba(255,255,255,0.3)]">{Math.round(currentSpeed)}</span>
                  <span className="text-[10px] sm:text-xs font-mono text-cyan-500/80 tracking-widest mt-1">%</span>
                </div>
              </div>
            </div>

            <div className="bg-white/[0.03] backdrop-blur-xl p-5 sm:p-8 rounded-lg border border-white/10 shadow-2xl flex flex-col items-center">
              <div className="flex justify-between items-center w-full mb-6 sm:mb-8">
                <h3 className="text-[10px] sm:text-xs font-bold text-slate-400 tracking-widest uppercase">Navegacao Manual</h3>
                <div className="text-[8px] sm:text-[10px] text-slate-500 border border-white/10 px-2 py-1 rounded bg-black/30 hidden sm:block">WASD / SETAS</div>
              </div>

              <div className="grid grid-cols-3 gap-2 sm:gap-3 justify-items-center">
                <div />
                <ControlButton icon={ArrowUp} direction="Frente" />
                <div />
                <ControlButton icon={ArrowLeft} direction="Esquerda" />
                <button
                  type="button"
                  onMouseDown={handleStop}
                  onTouchStart={(e) => {
                    e.preventDefault();
                    handleStop();
                  }}
                  className="relative flex items-center justify-center w-16 h-16 sm:w-20 sm:h-20 rounded-lg bg-red-500/10 border border-red-500/30 text-red-500 hover:bg-red-500/20 transition-all active:scale-95 shadow-[inset_0_0_20px_rgba(239,68,68,0.1)] select-none touch-none"
                  title="Parar"
                >
                  <StopCircle size={28} />
                </button>
                <ControlButton icon={ArrowRight} direction="Direita" />
                <div />
                <ControlButton icon={ArrowDown} direction="Trás" />
                <div />
              </div>
            </div>

            <div className="bg-white/[0.03] backdrop-blur-xl p-5 sm:p-6 rounded-lg border border-white/10 shadow-2xl">
              <div className="flex justify-between items-end mb-4">
                <div className="flex items-center gap-2">
                  <AlertTriangle size={14} className="text-amber-500" />
                  <h3 className="text-[10px] sm:text-xs font-bold text-slate-400 tracking-widest uppercase">Potencia Max</h3>
                </div>
                <span className="text-base sm:text-lg font-black font-mono text-cyan-400 drop-shadow-[0_0_8px_rgba(34,211,238,0.5)]">{speedLimit}%</span>
              </div>

              <div className="relative py-4">
                <div className="absolute w-full h-2 bg-white/5 rounded-full top-1/2 -translate-y-1/2 border border-white/5" />
                <div className="absolute h-2 bg-gradient-to-r from-cyan-600 to-cyan-400 rounded-full top-1/2 -translate-y-1/2 shadow-[0_0_10px_rgba(34,211,238,0.5)] pointer-events-none transition-all duration-150" style={{ width: `${speedLimit}%` }} />
                <input type="range" min="10" max="100" step="5" value={speedLimit} onChange={(e) => setSpeedLimit(Number(e.target.value))} className="absolute top-1/2 -translate-y-1/2 w-full h-full opacity-0 cursor-pointer z-10 touch-none" />
                <div className="absolute w-4 h-4 sm:w-5 sm:h-5 bg-white border-2 border-cyan-400 rounded-full top-1/2 -translate-y-1/2 shadow-[0_0_15px_rgba(34,211,238,0.8)] pointer-events-none transition-all duration-150" style={{ left: `calc(${speedLimit}% - 10px)` }} />
              </div>
            </div>
          </div>

          <div className="lg:col-span-8 order-3">
            <div className="bg-white/[0.02] backdrop-blur-xl p-4 sm:p-5 rounded-lg border border-white/5 shadow-xl h-48 sm:h-64 flex flex-col">
              <div className="flex items-center gap-2 mb-3 sm:mb-4 shrink-0">
                <TerminalSquare size={16} className="text-indigo-400" />
                <h3 className="text-[10px] sm:text-xs font-bold text-slate-300 tracking-wider">TERMINAL DE COMANDOS</h3>
              </div>
              <div className="overflow-y-auto flex-1 pr-2 space-y-1 font-mono text-[10px] sm:text-xs flex flex-col">
                {logs.map((log, index) => (
                  <div key={`${log.time}-${index}`} className={`flex gap-2 sm:gap-3 py-1 border-b border-white/5 last:border-0 ${index === 0 ? 'text-cyan-400' : 'text-slate-500'}`}>
                    <span className="opacity-70 shrink-0">[{log.time}]</span>
                    <span className="break-words">{log.msg}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
