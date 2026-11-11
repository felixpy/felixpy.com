import { useEffect, useRef, useState } from 'react';
import { tracks } from './library';

const defaultVolume = 0.5;
const trackIndex = (index: number) => (index + tracks.length) % tracks.length;
const silence = { bass: 0, mid: 0, beat: 0 };
type Analysis = {
  context: AudioContext;
  analyser: AnalyserNode;
  bins: Uint8Array<ArrayBuffer>;
  baseline: number;
};

export function useStudioMusic(enabled = true) {
  const audio = useRef<HTMLAudioElement | null>(null);
  const position = useRef(0);
  const automatic = useRef(true);
  const shuffleMode = useRef(false);
  const analysis = useRef<Analysis | null>(null);
  const openingAnalysis = useRef<AudioContext | null>(null);
  const [index, setIndex] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolume] = useState(defaultVolume);
  const [muted, setMuted] = useState(false);
  const [failed, setFailed] = useState(false);
  const [shuffle, setShuffle] = useState(false);
  const [repeat, setRepeat] = useState(false);

  function adjacent(direction: number) {
    const step =
      shuffleMode.current && direction > 0
        ? 1 + Math.floor(Math.random() * (tracks.length - 1))
        : direction;
    return trackIndex(position.current + step);
  }

  function play(next: number) {
    const player = audio.current;
    if (!player) return;
    if (!player.getAttribute('src') || position.current !== next || player.error) {
      position.current = next;
      setIndex(next);
      setElapsed(0);
      setDuration(0);
      setFailed(false);
      player.src = '/media/audio/music/' + tracks[next].file + '.mp3';
    }
    if (document.hidden) return;
    void player.play().catch((error: DOMException) => {
      if (
        audio.current === player &&
        error.name !== 'NotAllowedError' &&
        error.name !== 'AbortError'
      )
        setFailed(true);
    });
  }

  function listen() {
    const player = audio.current;
    if (!player || analysis.current || openingAnalysis.current || !window.AudioContext) return;
    const context = new AudioContext();
    openingAnalysis.current = context;
    void context
      .resume()
      .then(() => {
        if (audio.current !== player) return;
        const analyser = context.createAnalyser();
        analyser.fftSize = 1024;
        analyser.smoothingTimeConstant = 0.46;
        analyser.minDecibels = -83;
        analyser.maxDecibels = -24;
        context.createMediaElementSource(player).connect(analyser).connect(context.destination);
        analysis.current = {
          context,
          analyser,
          bins: new Uint8Array(analyser.frequencyBinCount),
          baseline: 0,
        };
      })
      .catch(() => {
        if (context.state !== 'closed') void context.close();
      })
      .finally(() => {
        if (openingAnalysis.current === context) openingAnalysis.current = null;
      });
  }

  useEffect(() => {
    if (!enabled) return;
    const player = new Audio();
    player.volume = volume;
    player.muted = muted;
    player.loop = repeat;
    player.preload = 'none';
    audio.current = player;
    const updateTime = () => setElapsed(player.currentTime);
    const updateDuration = () =>
      setDuration(Number.isFinite(player.duration) ? player.duration : 0);
    const began = () => {
      if (document.hidden) {
        player.pause();
        return;
      }
      setPlaying(true);
      setFailed(false);
      automatic.current = false;
    };
    const stopped = () => setPlaying(false);
    const error = () => setFailed(true);
    const ended = () => play(adjacent(1));
    let resumeOnVisible = false;
    const visibility = () => {
      if (document.hidden) {
        resumeOnVisible = !player.paused;
        player.pause();
      } else if (resumeOnVisible || automatic.current) {
        resumeOnVisible = false;
        play(position.current);
      }
    };
    const unlock = (event: Event) => {
      if (!event.isTrusted || document.hidden) return;
      // Mouse activates on press. Touch and pen activate on release.
      if (event instanceof PointerEvent && event.type !== 'click') {
        const activation = event.pointerType === 'mouse' ? 'pointerdown' : 'pointerup';
        if (!event.isPrimary || event.button !== 0 || event.type !== activation) return;
      }
      listen();
      if (
        !automatic.current ||
        !player.paused ||
        (event.target instanceof Element && event.target.closest('[data-music-control]'))
      )
        return;
      play(position.current);
    };
    const activationEvents = ['pointerdown', 'pointerup', 'click', 'keydown'];
    player.addEventListener('timeupdate', updateTime);
    player.addEventListener('durationchange', updateDuration);
    player.addEventListener('playing', began);
    player.addEventListener('pause', stopped);
    player.addEventListener('ended', ended);
    player.addEventListener('error', error);
    for (const event of activationEvents) window.addEventListener(event, unlock, true);
    document.addEventListener('visibilitychange', visibility);
    play(position.current);
    return () => {
      audio.current = null;
      automatic.current = true;
      const context = analysis.current?.context ?? openingAnalysis.current;
      analysis.current = openingAnalysis.current = null;
      if (context && context.state !== 'closed') void context.close();
      for (const event of activationEvents) window.removeEventListener(event, unlock, true);
      document.removeEventListener('visibilitychange', visibility);
      player.removeEventListener('timeupdate', updateTime);
      player.removeEventListener('durationchange', updateDuration);
      player.removeEventListener('playing', began);
      player.removeEventListener('pause', stopped);
      player.removeEventListener('ended', ended);
      player.removeEventListener('error', error);
      player.pause();
      player.removeAttribute('src');
      player.load();
    };
  }, [enabled]);

  return {
    index,
    playing,
    elapsed,
    duration,
    volume,
    muted,
    failed,
    shuffle,
    repeat,
    select(next: number) {
      listen();
      automatic.current = false;
      play(trackIndex(next));
    },
    step(direction: number) {
      listen();
      automatic.current = false;
      play(adjacent(direction));
    },
    playCollection(shuffled = shuffleMode.current) {
      listen();
      automatic.current = false;
      shuffleMode.current = shuffled;
      setShuffle(shuffled);
      const next = shuffled ? adjacent(1) : 0;
      if (audio.current && next === position.current) audio.current.currentTime = 0;
      play(next);
    },
    toggleShuffle() {
      shuffleMode.current = !shuffleMode.current;
      setShuffle(shuffleMode.current);
    },
    toggleRepeat() {
      const next = !repeat;
      if (audio.current) audio.current.loop = next;
      setRepeat(next);
    },
    toggle() {
      const player = audio.current;
      if (!player) return;
      listen();
      automatic.current = false;
      if (player.paused) play(position.current);
      else player.pause();
    },
    seek(seconds: number) {
      if (audio.current && duration > 0) audio.current.currentTime = seconds;
    },
    setVolume(value: number) {
      if (audio.current) audio.current.volume = value;
      setVolume(value);
    },
    toggleMute() {
      if (!audio.current) return;
      audio.current.muted = !audio.current.muted;
      setMuted(audio.current.muted);
    },
    spectrum(output: Float32Array) {
      const player = audio.current,
        meter = analysis.current;
      if (!meter || !player || player.paused || player.muted || player.volume === 0) {
        output.fill(0);
        return;
      }
      meter.analyser.getByteFrequencyData(meter.bins);
      for (let i = 0; i < output.length; i++) {
        const band = 1 + Math.round((i / output.length) ** 2 * 176);
        output[i] = meter.bins[band] / 255;
      }
    },
    levels() {
      const player = audio.current,
        meter = analysis.current;
      if (!meter || !player || player.paused || player.muted || player.volume === 0) return silence;
      meter.analyser.getByteFrequencyData(meter.bins);
      const band = (from: number, to: number) => {
        let sum = 0;
        for (let i = from; i < to; i++) sum += meter.bins[i];
        return sum / ((to - from) * 255);
      };
      const bass = band(1, 6),
        mid = band(6, 22);
      meter.baseline += (bass - meter.baseline) * 0.035;
      const beat = Math.min(1, Math.max(0, bass - meter.baseline - 0.022) * 5.8);
      return { bass, mid, beat };
    },
  };
}

export type StudioMusic = ReturnType<typeof useStudioMusic>;
