import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import { 
  Play, 
  Pause, 
  Square, 
  Volume2, 
  VolumeX, 
  Download, 
  Sparkles, 
  Loader2, 
  Gauge,
  UserCheck
} from 'lucide-react';

interface AudioPlayerProps {
  text: string;
  title?: string;
  sectionName?: string;
  onCloseSection?: () => void;
  apiBase?: string;
}

const VOICES = [
  { id: 'pt-BR-FranciscaNeural', label: 'Francisca (Voz Feminina)', short: 'Francisca ♀' },
  { id: 'pt-BR-AntonioNeural', label: 'Antônio (Voz Masculina)', short: 'Antônio ♂' },
  { id: 'pt-BR-ThalitaNeural', label: 'Thalita (Voz Expressiva)', short: 'Thalita ♀' },
];

const SPEEDS = [1.0, 1.25, 1.5, 2.0];

export const AudioPlayer: React.FC<AudioPlayerProps> = ({
  text,
  title = "Narraçāo dos Insights com IA",
  sectionName,
  onCloseSection,
  apiBase = "http://localhost:8000"
}) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [playbackRate, setPlaybackRate] = useState(1.0);
  const [selectedVoice, setSelectedVoice] = useState(VOICES[0].id);
  const [isMuted, setIsMuted] = useState(false);
  const [audioBlobUrl, setAudioBlobUrl] = useState<string | null>(null);
  const [usingFallback, setUsingFallback] = useState(false);

  const audioRef = useRef<HTMLAudioElement | null>(null);
  const currentTextRef = useRef<string>(text);
  const currentVoiceRef = useRef<string>(selectedVoice);

  // Stop playback when text changes
  useEffect(() => {
    if (currentTextRef.current !== text) {
      currentTextRef.current = text;
      handleStop();
      setAudioBlobUrl(null);
    }
  }, [text]);

  const cleanTextForSpeech = (rawText: string) => {
    return rawText
      .replace(/```[\s\S]*?```/g, '')
      .replace(/#+\s*/g, '')
      .replace(/[*_]{1,3}/g, '')
      .replace(/^\s*[-*•]\s+/gm, '')
      .replace(/^\s*\d+\.\s+/gm, '')
      .replace(/\n+/g, '. ')
      .trim();
  };

  const handlePlayFallbackSpeech = () => {
    if (!('speechSynthesis' in window)) {
      alert("Seu navegador não suporta síntese de voz.");
      return;
    }

    if (window.speechSynthesis.paused) {
      window.speechSynthesis.resume();
      setIsPlaying(true);
      return;
    }

    if (window.speechSynthesis.speaking) {
      window.speechSynthesis.pause();
      setIsPlaying(false);
      return;
    }

    window.speechSynthesis.cancel();
    const clean = cleanTextForSpeech(text);
    const utterance = new SpeechSynthesisUtterance(clean);
    utterance.lang = 'pt-BR';
    utterance.rate = playbackRate;
    
    utterance.onstart = () => {
      setIsLoading(false);
      setIsPlaying(true);
      setUsingFallback(true);
    };

    utterance.onend = () => {
      setIsPlaying(false);
      setUsingFallback(false);
      setCurrentTime(0);
    };

    utterance.onerror = () => {
      setIsPlaying(false);
      setIsLoading(false);
      setUsingFallback(false);
    };

    window.speechSynthesis.speak(utterance);
  };

  const fetchAndPlayAudio = async () => {
    if (!text || !text.trim()) return;

    // Check if we already have the generated audio blob for the current text + voice
    if (audioBlobUrl && currentVoiceRef.current === selectedVoice && audioRef.current) {
      try {
        await audioRef.current.play();
        setIsPlaying(true);
        return;
      } catch {
        // Continue to re-fetch if play failed
      }
    }

    setIsLoading(true);
    try {
      const response = await axios.post(
        `${apiBase}/tts`,
        { text, voice: selectedVoice },
        { responseType: 'blob', timeout: 15000 }
      );

      const blob = new Blob([response.data], { type: 'audio/mpeg' });
      const url = URL.createObjectURL(blob);
      setAudioBlobUrl(url);
      currentVoiceRef.current = selectedVoice;

      if (audioRef.current) {
        audioRef.current.src = url;
        audioRef.current.playbackRate = playbackRate;
        await audioRef.current.play();
        setIsPlaying(true);
      }
    } catch (err) {
      console.warn("Backend TTS failed, using browser SpeechSynthesis fallback", err);
      handlePlayFallbackSpeech();
    } finally {
      setIsLoading(false);
    }
  };

  const handleTogglePlay = () => {
    if (usingFallback) {
      handlePlayFallbackSpeech();
      return;
    }

    if (isPlaying && audioRef.current) {
      audioRef.current.pause();
      setIsPlaying(false);
    } else {
      fetchAndPlayAudio();
    }
  };

  const handleStop = () => {
    if (window.speechSynthesis) {
      window.speechSynthesis.cancel();
    }
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
    }
    setIsPlaying(false);
    setIsLoading(false);
    setCurrentTime(0);
    setUsingFallback(false);
  };

  const handleSeek = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newTime = parseFloat(e.target.value);
    setCurrentTime(newTime);
    if (audioRef.current) {
      audioRef.current.currentTime = newTime;
    }
  };

  const handleSpeedChange = () => {
    const currentIndex = SPEEDS.indexOf(playbackRate);
    const nextSpeed = SPEEDS[(currentIndex + 1) % SPEEDS.length];
    setPlaybackRate(nextSpeed);
    if (audioRef.current) {
      audioRef.current.playbackRate = nextSpeed;
    }
    if (usingFallback && window.speechSynthesis.speaking) {
      // Re-trigger with new rate if using native speech
      handleStop();
      setTimeout(handlePlayFallbackSpeech, 100);
    }
  };

  const handleVoiceChange = (voiceId: string) => {
    if (voiceId === selectedVoice) return;
    setSelectedVoice(voiceId);
    handleStop();
    setAudioBlobUrl(null);
  };

  const handleToggleMute = () => {
    if (audioRef.current) {
      audioRef.current.muted = !isMuted;
      setIsMuted(!isMuted);
    }
  };

  const handleDownload = () => {
    if (!audioBlobUrl) {
      alert("Reproduza o áudio primeiro para gerar o arquivo MP3 para download.");
      return;
    }
    const a = document.createElement('a');
    a.href = audioBlobUrl;
    a.download = `insights_audio_${sectionName || 'geral'}.mp3`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  };

  const formatTime = (seconds: number) => {
    if (isNaN(seconds) || seconds < 0) return "00:00";
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className={`audio-player-wrapper ${isPlaying ? 'playing' : ''}`}>
      <audio
        ref={audioRef}
        onTimeUpdate={() => audioRef.current && setCurrentTime(audioRef.current.currentTime)}
        onLoadedMetadata={() => audioRef.current && setDuration(audioRef.current.duration)}
        onEnded={() => {
          setIsPlaying(false);
          setCurrentTime(0);
        }}
      />

      <div className="audio-player-header">
        <div className="audio-title-info">
          <div className="audio-icon-badge">
            <Sparkles size={16} className="text-indigo-600 animate-pulse" />
          </div>
          <div>
            <div className="audio-title">{sectionName ? `Ouvindo: ${sectionName}` : title}</div>
            <div className="audio-subtitle">
              {usingFallback 
                ? 'Voz Nativa do Navegador (Modo Offline)' 
                : 'Voz Neural de Alta Definição (Português Brasil)'}
            </div>
          </div>
        </div>

        {/* Voice Selector & Actions */}
        <div className="audio-options-group">
          <div className="voice-selector">
            <UserCheck size={14} />
            <select 
              value={selectedVoice} 
              onChange={(e) => handleVoiceChange(e.target.value)}
              disabled={isPlaying || isLoading}
              title="Escolher Voz Neural"
            >
              {VOICES.map(v => (
                <option key={v.id} value={v.id}>{v.short}</option>
              ))}
            </select>
          </div>

          {sectionName && onCloseSection && (
            <button 
              onClick={() => { handleStop(); onCloseSection(); }}
              className="btn-close-section"
              title="Voltar para áudio geral"
            >
              Ouvir Tudo
            </button>
          )}
        </div>
      </div>

      {/* Controls & Progress Bar */}
      <div className="audio-player-body">
        <div className="audio-controls-primary">
          <button 
            onClick={handleTogglePlay}
            disabled={isLoading}
            className={`btn-play-pause ${isPlaying ? 'active' : ''}`}
            title={isPlaying ? "Pausar" : "Reproduzir áudio"}
          >
            {isLoading ? (
              <Loader2 size={20} className="animate-spin" />
            ) : isPlaying ? (
              <Pause size={20} />
            ) : (
              <Play size={20} style={{ marginLeft: '2px' }} />
            )}
          </button>

          <button 
            onClick={handleStop}
            disabled={!isPlaying && currentTime === 0 && !isLoading}
            className="btn-audio-action"
            title="Parar reprodução"
          >
            <Square size={16} />
          </button>

          {/* Animated sound wave equalizer */}
          <div className={`sound-wave ${isPlaying ? 'active' : ''}`}>
            <span className="wave-bar"></span>
            <span className="wave-bar"></span>
            <span className="wave-bar"></span>
            <span className="wave-bar"></span>
            <span className="wave-bar"></span>
          </div>
        </div>

        {/* Progress Slider */}
        <div className="audio-progress-section">
          <span className="audio-time">{formatTime(currentTime)}</span>
          <input
            type="range"
            min="0"
            max={duration || 100}
            step="0.1"
            value={currentTime}
            onChange={handleSeek}
            disabled={usingFallback || !duration}
            className="audio-slider"
            style={{
              background: duration 
                ? `linear-gradient(to right, var(--primary) ${(currentTime / duration) * 100}%, #e2e8f0 ${(currentTime / duration) * 100}%)`
                : '#e2e8f0'
            }}
          />
          <span className="audio-time">{formatTime(duration)}</span>
        </div>

        {/* Secondary Controls (Speed, Volume, Download) */}
        <div className="audio-controls-secondary">
          <button 
            onClick={handleSpeedChange} 
            className="btn-speed-pill"
            title="Alterar Velocidade de Reprodução"
          >
            <Gauge size={14} />
            <span>{playbackRate}x</span>
          </button>

          <button 
            onClick={handleToggleMute}
            className="btn-audio-action"
            title={isMuted ? "Ativar Som" : "Mudo"}
          >
            {isMuted ? <VolumeX size={16} /> : <Volume2 size={16} />}
          </button>

          {audioBlobUrl && (
            <button 
              onClick={handleDownload}
              className="btn-audio-action download-btn"
              title="Baixar MP3 da narração"
            >
              <Download size={16} />
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
export default AudioPlayer;
