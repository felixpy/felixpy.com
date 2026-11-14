import {
  Disc3,
  ListMusic,
  Maximize2,
  Music2,
  Pause,
  Play,
  Repeat1,
  Search,
  Shuffle,
  SkipBack,
  SkipForward,
  Volume2,
  VolumeX,
} from 'lucide-react';
import { useRef, useState, type CSSProperties } from 'react';
import { local, type Locale } from '../../../app/locale';
import Shader from '../../../spectral/Shader';
import musicRoom from '../../../spectral/shaders/music-room.glsl?raw';
import { artist, collectionLength, timestamp, tracks } from './library';
import Spectrum from './Spectrum';
import type { StudioMusic } from './useStudioMusic';

export function MusicPlayer({
  locale,
  music,
  active,
  reducedMotion,
}: {
  locale: Locale;
  music: StudioMusic;
  active: boolean;
  reducedMotion: boolean;
}) {
  const t = (en: string, zh: string) => local(locale, en, zh);
  const track = tracks[music.index];
  const duration = music.duration || track.length;
  const animate = active && music.playing && !reducedMotion;
  const [playlistOpen, setPlaylistOpen] = useState(false);
  const [query, setQuery] = useState('');
  const activeRow = useRef<HTMLButtonElement>(null);
  const search = query.trim().toLocaleLowerCase();
  const shownTracks = tracks
    .map((item, index) => ({ item, index }))
    .filter(({ item }) =>
      [item.name, ...item.mood].some((value) => value.toLocaleLowerCase().includes(search)),
    );
  const collection = t('Late-night focus', '深夜专注');

  function record() {
    return (
      <div className="spectral-record" aria-hidden="true">
        <img
          src="/media/interface/vinyl-record.webp"
          alt=""
          width={900}
          height={900}
          data-spinning={animate}
        />
      </div>
    );
  }
  function seek(inline = false) {
    return (
      <div className={inline ? 'spectral-mini-seek' : 'spectral-seek'}>
        {inline && <time>{timestamp(music.elapsed)}</time>}
        <input
          className="spectral-slider"
          type="range"
          aria-label={t('Playback position', '播放进度')}
          min={0}
          max={duration}
          step={0.1}
          value={Math.min(music.elapsed, duration)}
          disabled={!music.duration}
          onChange={(event) => music.seek(event.target.valueAsNumber)}
          style={{ '--progress': (music.elapsed / duration) * 100 + '%' } as CSSProperties}
        />
        {inline ? (
          <time>{timestamp(duration)}</time>
        ) : (
          <div className="spectral-time">
            <time>{timestamp(music.elapsed)}</time>
            <time>{timestamp(duration)}</time>
          </div>
        )}
      </div>
    );
  }
  function controls(expanded = false) {
    return (
      <div className="spectral-skip">
        {expanded && (
          <button
            type="button"
            aria-label={t('Shuffle', '随机播放')}
            aria-pressed={music.shuffle}
            onClick={music.toggleShuffle}
          >
            <Shuffle />
          </button>
        )}
        <button
          type="button"
          aria-label={t('Previous track', '上一首')}
          onClick={() => music.step(-1)}
        >
          <SkipBack />
        </button>
        <button
          type="button"
          className="spectral-play"
          aria-label={music.playing ? t('Pause', '暂停') : t('Play', '播放')}
          onClick={music.toggle}
        >
          {music.playing ? <Pause /> : <Play />}
        </button>
        <button type="button" aria-label={t('Next track', '下一首')} onClick={() => music.step(1)}>
          <SkipForward />
        </button>
        {expanded && (
          <button
            type="button"
            aria-label={t('Repeat track', '单曲循环')}
            aria-pressed={music.repeat}
            onClick={music.toggleRepeat}
          >
            <Repeat1 />
          </button>
        )}
      </div>
    );
  }
  function volume() {
    return (
      <div className="spectral-volume">
        <button
          type="button"
          aria-label={music.muted ? t('Unmute', '取消静音') : t('Mute', '静音')}
          onClick={music.toggleMute}
        >
          {music.muted ? <VolumeX /> : <Volume2 />}
        </button>
        <input
          className="spectral-slider"
          type="range"
          min={0}
          max={1}
          step={0.01}
          value={music.volume}
          aria-label={t('Volume', '音量')}
          onChange={(event) => music.setVolume(event.target.valueAsNumber)}
          style={{ '--progress': music.volume * 100 + '%' } as CSSProperties}
        />
      </div>
    );
  }
  const failure = music.failed && (
    <p className="spectral-error" role="status">
      {t('Press Play to retry, or skip to the next track.', '可按播放重试，或切到下一首。')}
    </p>
  );
  return (
    <section
      className={'spectral spectral-player' + (playlistOpen ? ' spectral-collection-open' : '')}
      data-music-control
      aria-label={t('Music player', '音乐播放器')}
      onKeyDown={(event) => {
        if (event.key === 'Escape' && playlistOpen) {
          event.preventDefault();
          event.stopPropagation();
          setPlaylistOpen(false);
        }
      }}
    >
      <div className="spectral-background">
        <Shader fragment={musicRoom} />
      </div>
      <header className="spectral-heading spectral-music-heading">
        <span className="spectral-music-title">{t('Listening room', '听音室')}</span>
        <nav className="spectral-music-tabs" aria-label={t('Music views', '播放器视图')}>
          <button type="button" aria-pressed={!playlistOpen} onClick={() => setPlaylistOpen(false)}>
            <Disc3 />
            {t('Player', '播放器')}
          </button>
          <button type="button" aria-pressed={playlistOpen} onClick={() => setPlaylistOpen(true)}>
            {t('Playlist', '播放列表')}
          </button>
        </nav>
        <span className="spectral-music-signature">FELIX.PY</span>
      </header>
      {!playlistOpen ? (
        <>
          <div className="spectral-player-content">
            {record()}
            <div className="spectral-transport">
              <div className="spectral-playing">
                <Music2 />
                {music.playing ? t('Now playing', '正在播放') : t('Listening room', '听音室')}
              </div>
              <h1>{track.name}</h1>
              <p className="spectral-artist">{artist}</p>
              <Spectrum read={music.spectrum} animate={animate} />
              {seek()}
              <div className="spectral-player-actions">
                {controls()}
                {volume()}
              </div>
              {failure}
            </div>
          </div>
          <footer className="spectral-player-footer">
            {t('Taste Is All You Need', '审美，就是一切')}
          </footer>
        </>
      ) : (
        <>
          <div className="spectral-collection">
            <aside className="spectral-collection-detail">
              {record()}
              <h2>{collection}</h2>
              <p>{t('Ambient textures for uninterrupted hours.', '让专注多停留一会儿的音乐。')}</p>
              <small>
                {t(
                  `${tracks.length} tracks · ${Math.floor(collectionLength / 60)} min ${collectionLength % 60} sec`,
                  `${tracks.length} 首 · ${Math.floor(collectionLength / 60)} 分 ${collectionLength % 60} 秒`,
                )}
              </small>
              <div className="spectral-collection-actions">
                <button type="button" onClick={() => music.playCollection()}>
                  <Play />
                  {t('Play collection', '播放歌单')}
                </button>
                <button
                  type="button"
                  aria-label={t('Shuffle collection', '随机播放歌单')}
                  onClick={() => music.playCollection(true)}
                >
                  <Shuffle />
                </button>
              </div>
            </aside>
            <div className="spectral-queue">
              <div className="spectral-queue-title">
                <div>
                  <h1>{t('Playlist', '播放列表')}</h1>
                  <p>
                    {t('A little space to get lost in the music.', '留一点空间，沉浸在音乐里。')}
                  </p>
                </div>
                <label>
                  <Search />
                  <input
                    type="search"
                    value={query}
                    onChange={(event) => setQuery(event.target.value)}
                    aria-label={t('Search tracks', '搜索曲目')}
                    placeholder={t('Search tracks', '搜索曲目')}
                  />
                </label>
              </div>
              <div className="spectral-track-row spectral-track-heading" aria-hidden="true">
                <span>#</span>
                <span>{t('Title', '曲名')}</span>
                <span>{t('Mood', '氛围')}</span>
                <span>{t('Time', '时长')}</span>
              </div>
              <ol aria-label={t('Tracks', '曲目')}>
                {shownTracks.map(({ item, index }) => {
                  const current = index === music.index;
                  return (
                    <li key={item.file}>
                      <button
                        type="button"
                        className="spectral-track-row"
                        ref={current ? activeRow : null}
                        aria-current={current ? 'true' : undefined}
                        onClick={() => music.select(index)}
                      >
                        <span aria-hidden="true">
                          {current && music.playing ? (
                            <Volume2 />
                          ) : (
                            String(index + 1).padStart(2, '0')
                          )}
                        </span>
                        <strong>{item.name}</strong>
                        <span>{t(item.mood[0], item.mood[1])}</span>
                        <time>{timestamp(item.length)}</time>
                      </button>
                    </li>
                  );
                })}
              </ol>
              {!shownTracks.length && (
                <p className="spectral-no-tracks" role="status">
                  {t('No tracks found.', '没有找到曲目。')}
                </p>
              )}
              {failure}
            </div>
          </div>
          <footer className="spectral-mini">
            <div className="spectral-mini-identity">
              <img src="/media/interface/vinyl-record.webp" alt="" width={56} height={56} />
              <div>
                <strong>{track.name}</strong>
                <small>{collection}</small>
              </div>
            </div>
            <div className="spectral-mini-center">
              {controls(true)}
              {seek(true)}
            </div>
            <div className="spectral-mini-tools">
              {volume()}
              <button
                type="button"
                aria-label={t('Show current track', '定位当前曲目')}
                onClick={() => {
                  setQuery('');
                  requestAnimationFrame(() =>
                    activeRow.current?.scrollIntoView({ block: 'nearest' }),
                  );
                }}
              >
                <ListMusic />
              </button>
              <button
                type="button"
                aria-label={t('Open player view', '返回播放器')}
                onClick={() => setPlaylistOpen(false)}
              >
                <Maximize2 />
              </button>
            </div>
          </footer>
        </>
      )}
    </section>
  );
}
