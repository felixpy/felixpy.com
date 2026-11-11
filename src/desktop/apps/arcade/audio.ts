type Cue = 'start' | 'pulse' | 'missile' | 'pickup' | 'hit' | 'destroy' | 'lost';
const voices: Record<
  Cue,
  { pitch: [number, number]; duration: number; gain: number; wave: OscillatorType }
> = {
  start: { pitch: [290, 720], duration: 0.22, gain: 0.09, wave: 'triangle' },
  pulse: { pitch: [650, 365], duration: 0.062, gain: 0.025, wave: 'square' },
  missile: { pitch: [270, 840], duration: 0.15, gain: 0.05, wave: 'triangle' },
  pickup: { pitch: [440, 1100], duration: 0.19, gain: 0.082, wave: 'triangle' },
  hit: { pitch: [130, 54], duration: 0.24, gain: 0.115, wave: 'sawtooth' },
  destroy: { pitch: [190, 65], duration: 0.15, gain: 0.06, wave: 'triangle' },
  lost: { pitch: [440, 79], duration: 0.43, gain: 0.098, wave: 'triangle' },
};

export function createArcadeAudio() {
  const context = new AudioContext();
  const bus = context.createGain();
  bus.gain.value = 0.46;
  const soften = context.createBiquadFilter();
  soften.type = 'lowpass';
  soften.frequency.value = 1700;
  bus.connect(soften).connect(context.destination);
  return {
    async start() {
      try {
        await context.resume();
      } catch {
        /* The game remains playable when audio is unavailable. */
      }
    },
    play(cue: Cue) {
      if (context.state !== 'running' || document.hidden) return;
      const { pitch, duration, gain, wave } = voices[cue];
      const now = context.currentTime;
      const oscillator = context.createOscillator();
      const envelope = context.createGain();
      oscillator.type = wave;
      oscillator.frequency.setValueAtTime(pitch[0], now);
      oscillator.frequency.exponentialRampToValueAtTime(pitch[1], now + duration * 0.86);
      envelope.gain.setValueAtTime(0.0001, now);
      envelope.gain.exponentialRampToValueAtTime(gain, now + 0.006);
      envelope.gain.exponentialRampToValueAtTime(0.0001, now + duration);
      oscillator.connect(envelope).connect(bus);
      oscillator.start(now);
      oscillator.stop(now + duration + 0.01);
    },
    setEnabled(enabled: boolean) {
      bus.gain.setTargetAtTime(enabled ? 0.46 : 0, context.currentTime, 0.03);
    },
    dispose() {
      if (context.state !== 'closed') void context.close();
    },
  };
}
