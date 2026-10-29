import { Brain, Camera, Gear } from "./Icons";

const STEPS = [
  [Camera, "A sky camera saves a clip of anything that moves across the night sky."],
  [Gear, "Our code measures it (speed, straightness, blinking)."],
  [Brain, "Muse Spark investigates: picks what to check, then decides and explains why."],
];

export default function HowItWorks() {
  return (
    <section className="block how" aria-label="How it works">
      <ol className="how__steps">
        {STEPS.map(([Icon, text], i) => (
          <li key={i}>
            <span className="how__num">{i + 1}</span>
            <span className="how__icon"><Icon /></span>
            <span className="how__text">{text}</span>
            {i < STEPS.length - 1 && <span className="how__arrow" aria-hidden="true">→</span>}
          </li>
        ))}
      </ol>
    </section>
  );
}
