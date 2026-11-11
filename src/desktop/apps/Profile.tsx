import { ArrowUpRight } from 'lucide-react';
import { biography, publicProfiles } from '../../content/profile';
import { local, type Locale } from '../../app/locale';
import Shader from '../../spectral/Shader';
import spectralHome from '../../spectral/shaders/profile.glsl?raw';
import spectralHomeMobile from '../../spectral/shaders/profile-mobile.glsl?raw';

export default function Profile({
  locale,
  animate,
  mobile = false,
}: {
  locale: Locale;
  animate: boolean;
  mobile?: boolean;
}) {
  const t = (en: string, zh: string) => local(locale, en, zh);
  const today = new Date();
  const workMonths =
    (today.getFullYear() - biography.first.started.year) * 12 +
    today.getMonth() +
    1 -
    biography.first.started.month;
  const workYears = Math.max(0, Math.floor(workMonths / 12));
  const careers = [
    { years: biography.school.years, name: t('Beihang University', biography.school.name) },
    {
      years: biography.first.years,
      name: t('Streaming video', biography.first.name),
      role: t('Engineering Manager', '技术经理'),
    },
    {
      years: t('2021 – NOW', biography.second.years),
      name: t('Short-form video', biography.second.name),
      role: t('Senior Software Engineer', biography.second.role),
    },
  ];
  return (
    <section
      className={'spectral spectral-profile' + (mobile ? ' spectral-profile-mobile' : '')}
      aria-label="Felix Yang"
    >
      <div className="spectral-background">
        <Shader
          fragment={mobile ? spectralHomeMobile : spectralHome}
          animate={animate}
          maxDpr={mobile ? 1 : 1.5}
        />
      </div>
      <header className="spectral-heading">
        <span className="spectral-wordmark">FELIX.PY</span>
        <nav aria-label={t('Social profiles', '社交主页')}>
          <a href={publicProfiles.github} target="_blank" rel="noopener noreferrer">
            GitHub <ArrowUpRight />
          </a>
          <a href={publicProfiles.x} target="_blank" rel="noopener noreferrer">
            X / Twitter <ArrowUpRight />
          </a>
        </nav>
      </header>
      <div className="spectral-introduction">
        <h1>
          {t('Taste Is All', '审美，')}
          <br />
          {t('You Need', '就是一切')}
        </h1>
        <p className="spectral-role">
          {t('Full-stack engineer & AI maker', '全栈工程师与 AI 创作者')}
        </p>
        <p className="spectral-statement">
          {t('I turn ideas into apps, videos and games.', '我把想法做成应用、视频和游戏。')}
          <br />
          {t('Then share what actually works.', '再分享真正有效的做法。')}
        </p>
        <a
          className="spectral-follow"
          href={publicProfiles.x}
          target="_blank"
          rel="noopener noreferrer"
        >
          {t('Follow on X', '在 X 上关注')} <ArrowUpRight />
        </a>
      </div>
      <p className="spectral-tenure">
        <strong>
          {t(`${workYears} ${workYears === 1 ? 'year' : 'years'}`, `${workYears} 年`)}
        </strong>
        <span>{t('Building. Learning. Repeating.', '做东西，学东西，再来一遍。')}</span>
      </p>
      <ol className="spectral-career" aria-label={t('Career timeline', '经历')}>
        {careers.map(({ years, name, role }) => (
          <li key={years}>
            <span>{years}</span>
            <h2>{name}</h2>
            {role && <p>{role}</p>}
          </li>
        ))}
      </ol>
    </section>
  );
}
