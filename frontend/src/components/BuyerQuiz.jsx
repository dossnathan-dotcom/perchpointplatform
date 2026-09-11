import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { ArrowRight, CheckCircle2, RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";

const questions = [
  {
    question: "When do you want to move?",
    options: [
      { label: "Within 60 days", score: 3 },
      { label: "In 3–6 months", score: 2 },
      { label: "Just exploring", score: 1 },
    ],
  },
  {
    question: "How ready is your financing?",
    options: [
      { label: "Pre-approved", score: 3 },
      { label: "Pre-qualified", score: 2 },
      { label: "Need lender guidance", score: 1 },
    ],
  },
  {
    question: "How clear is your Cincinnati neighborhood shortlist?",
    options: [
      { label: "I know my target area", score: 3 },
      { label: "I have 2–3 options", score: 2 },
      { label: "I need local guidance", score: 1 },
    ],
  },
  {
    question: "What would help you most right now?",
    options: [
      { label: "Private tour strategy", score: 3 },
      { label: "Neighborhood comparison", score: 2 },
      { label: "Budget and timing plan", score: 1 },
    ],
  },
];

const results = [
  {
    min: 10,
    title: "Tour-ready",
    copy: "You are positioned to move quickly. The next best step is a private tour strategy with exact target homes and offer timing.",
  },
  {
    min: 7,
    title: "Search-ready",
    copy: "You have strong momentum. A short advisor session can tighten your neighborhood list, budget guardrails, and showing plan.",
  },
  {
    min: 0,
    title: "Strategy-first",
    copy: "You will benefit from a clear local roadmap before touring. Start with financing, timing, and Cincinnati neighborhood fit.",
  },
];

export const BuyerQuiz = ({ onConsultation }) => {
  const [step, setStep] = useState(0);
  const [answers, setAnswers] = useState([]);
  const complete = answers.length === questions.length;
  const score = answers.reduce((total, value) => total + value, 0);
  const result = results.find((item) => score >= item.min);

  const choose = (option) => {
    const nextAnswers = [...answers, option.score];
    setAnswers(nextAnswers);
    setStep((current) => Math.min(current + 1, questions.length));
  };

  const restart = () => {
    setAnswers([]);
    setStep(0);
  };

  return (
    <section id="buyer-quiz" className="bg-obsidian py-24 text-linen sm:py-32" data-testid="buyer-quiz-section">
      <div className="mx-auto grid max-w-7xl gap-10 px-5 sm:px-8 lg:grid-cols-[0.8fr_1.2fr] lg:items-center">
        <div>
          <p className="kicker-line font-mono text-xs uppercase tracking-[0.3em] text-gold">Buyer readiness</p>
          <h2 className="mt-5 font-heading text-3xl font-bold tracking-tight sm:text-5xl">
            Know your next move before you tour another home.
          </h2>
          <p className="mt-6 max-w-xl text-base leading-8 text-linen/70">
            Answer four quick questions and get a practical recommendation for how to approach the Cincinnati market.
          </p>
        </div>

        <div className="rounded-[2rem] border border-white/10 bg-white/[0.06] p-6 shadow-2xl shadow-black/20 backdrop-blur sm:p-8">
          <div className="mb-7 h-2 overflow-hidden rounded-full bg-white/10">
            <div className="h-full rounded-full bg-gold transition-all duration-500" style={{ width: `${(answers.length / questions.length) * 100}%` }} />
          </div>

          <AnimatePresence mode="wait">
            {!complete ? (
              <motion.div
                key={step}
                initial={{ opacity: 0, x: 24 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -24 }}
                transition={{ duration: 0.35 }}
              >
                <p className="font-mono text-xs uppercase tracking-[0.24em] text-gold">Question {step + 1} of {questions.length}</p>
                <h3 className="mt-4 font-heading text-3xl font-bold" data-testid="quiz-question">{questions[step].question}</h3>
                <div className="mt-8 grid gap-3">
                  {questions[step].options.map((option, index) => (
                    <button
                      key={option.label}
                      onClick={() => choose(option)}
                      className="group flex items-center justify-between rounded-2xl border border-white/10 bg-white/[0.05] p-5 text-left font-semibold transition-all duration-300 hover:border-gold hover:bg-gold/10"
                      data-testid={`quiz-option-${index}`}
                    >
                      {option.label}
                      <ArrowRight className="h-4 w-4 text-linen/40 transition-transform group-hover:translate-x-1 group-hover:text-gold" />
                    </button>
                  ))}
                </div>
              </motion.div>
            ) : (
              <motion.div
                key="result"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4 }}
                className="rounded-[1.5rem] border border-gold/25 bg-gold/10 p-7"
                data-testid="quiz-result-card"
              >
                <CheckCircle2 className="mb-5 h-8 w-8 text-gold" />
                <p className="font-mono text-xs uppercase tracking-[0.24em] text-gold">Your readiness signal</p>
                <h3 className="mt-3 font-heading text-4xl font-bold">{result.title}</h3>
                <p className="mt-4 leading-7 text-linen/70">{result.copy}</p>
                <div className="mt-8 flex flex-col gap-3 sm:flex-row">
                  <Button className="rounded-full bg-gold text-obsidian hover:bg-goldSoft" onClick={onConsultation} data-testid="quiz-consultation-btn">
                    Book My Consultation <ArrowRight className="h-4 w-4" />
                  </Button>
                  <Button variant="outline" className="rounded-full border-white/15 bg-transparent text-linen hover:bg-white/10 hover:text-linen" onClick={restart} data-testid="quiz-restart-btn">
                    <RotateCcw className="h-4 w-4" /> Retake Quiz
                  </Button>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </section>
  );
};
