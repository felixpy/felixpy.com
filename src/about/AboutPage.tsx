import { ArrowUpRight } from 'lucide-react';
import { aboutPage as copy, formatWorkYears } from '../content/about';
import { getWorkYears, publicProfiles } from '../content/profile';

export default function AboutPage() {
  return (
    <main className="about-page">
      <div className="about-light" aria-hidden="true" />
      <header className="about-header">
        <a className="about-wordmark" href="/">
          FELIX.PY
        </a>
      </header>

      <section className="about-hero" aria-labelledby="about-name">
        <div className="about-introduction">
          <h1 id="about-name">{copy.heading}</h1>
          <p className="about-role">{copy.subtitle}</p>
          <p>
            {copy.introduction[0]} <br />
            {copy.introduction[1]}
          </p>
          <p className="about-practice">
            {copy.practice[0]} <br />
            {copy.practice[1]}
          </p>
        </div>
        <div className="about-experience">
          <p id="about-years">{formatWorkYears(getWorkYears())}</p>
          <p>{copy.experience}</p>
        </div>
      </section>

      <section className="about-career" aria-labelledby="career-heading">
        <h2 id="career-heading">{copy.career}</h2>
        <ol>
          {copy.timeline.map(([years, title, role]) => (
            <li key={years}>
              <p>{years}</p>
              <h3>{title}</h3>
              <p>{role}</p>
            </li>
          ))}
        </ol>
      </section>

      <section className="about-invitation" aria-labelledby="studio-heading">
        <div>
          <h2 id="studio-heading">{copy.studio}</h2>
          <p>{copy.studioDescription}</p>
        </div>
        <a href="/">
          {copy.explore} <ArrowUpRight aria-hidden="true" />
        </a>
      </section>

      <footer className="about-footer">
        <p>{copy.motto}</p>
        <div>
          <a href={publicProfiles.githubProfile}>
            {copy.github} <ArrowUpRight aria-hidden="true" />
          </a>
          <a className="about-follow" href={publicProfiles.x}>
            {copy.x} <ArrowUpRight aria-hidden="true" />
          </a>
        </div>
      </footer>
    </main>
  );
}
