import { motion, MotionConfig, useReducedMotion } from 'motion/react'
import './LandingPage.css'

type LandingPageProps = { onWorkspace: () => void; onDemo: () => void }

export function LandingPage({ onWorkspace, onDemo }: LandingPageProps) {
  const reduceMotion = useReducedMotion()
  const rise = (delay: number) => ({
    initial: reduceMotion ? false as const : { y: 18 },
    animate: { y: 0 },
    transition: { duration: 0.55, delay, ease: 'easeOut' as const },
  })
  const hover = reduceMotion ? undefined : { y: -2 }

  return <MotionConfig reducedMotion="user"><div className="landing">
    <motion.header className="landing-nav" {...rise(0)}>
      <a className="landing-logo" href="/" aria-label="ClassLens home"><img className="landing-logo__image" src="/classlens-mascot.png" alt="" width="60" height="60" /><span>ClassLens</span></a>
      <nav aria-label="Landing page"><a href="#how-it-works">How it works</a><button onClick={onWorkspace}>Open workspace <span aria-hidden="true">↗</span></button></nav>
    </motion.header>
    <main>
      <section className="landing-hero" aria-labelledby="landing-title">
        <div className="landing-hero__copy">
          <motion.p className="landing-overline" {...rise(0.08)}>For teachers who want to know why</motion.p>
          <motion.h1 id="landing-title" {...rise(0.16)}>From grades to <em>understanding.</em></motion.h1>
          <motion.p className="landing-hero__lede" {...rise(0.25)}>A score shows who needs help. ClassLens helps you see recurring ideas in students’ own words, check the evidence, and choose what to teach next.</motion.p>
          <motion.div className="landing-actions" {...rise(0.34)}><motion.button className="landing-action landing-action--primary" onClick={onWorkspace} whileHover={hover} whileTap={reduceMotion ? undefined : { scale: 0.98 }}>Open teacher workspace <span aria-hidden="true">→</span></motion.button><motion.button className="landing-action landing-action--text" onClick={onDemo} whileHover={hover} whileTap={reduceMotion ? undefined : { scale: 0.98 }}>Try the synthetic demo <span aria-hidden="true">↗</span></motion.button></motion.div>
          <motion.p className="landing-demo-note" {...rise(0.4)}>The photosynthesis demo uses synthetic student data.</motion.p>
        </div>
        <motion.div className="landing-hero__visual" aria-label="Illustration of a teacher reviewing a response pattern and its evidence" role="img" initial={reduceMotion ? false : { x: 22, y: 12 }} animate={{ x: 0, y: 0 }} transition={{ duration: 0.8, delay: 0.22, ease: 'easeOut' }}>
          <div className="landing-visual__top"><span>CLASSLENS / TEACHER VIEW</span><span>01—03</span></div>
          <div className="landing-visual__question">What are students<br />thinking?</div>
          <div className="landing-visual__path"><span>Student responses</span><i aria-hidden="true" /><span>Recurring pattern</span><i aria-hidden="true" /><span>Teacher review</span></div>
          <motion.div className="landing-visual__focus" aria-hidden="true" animate={reduceMotion ? undefined : { opacity: [0.7, 1, 0.7] }} transition={{ duration: 5, repeat: Infinity, ease: 'easeInOut' }}><span /><span /><span /></motion.div>
          <div className="landing-visual__bottom"><span>Evidence stays visible.</span><span className="landing-visual__asterisk">✳</span></div>
        </motion.div>
      </section>
      <section className="landing-process" id="how-it-works" aria-labelledby="process-title">
        <motion.div className="landing-section-heading" initial={reduceMotion ? false : { y: 20 }} whileInView={{ y: 0 }} viewport={{ once: true, amount: 0.3 }} transition={{ duration: 0.55 }}><p className="landing-overline">A clear path from response to response</p><h2 id="process-title">See the pattern. Check the evidence. Make the call.</h2></motion.div>
        <div className="landing-process__steps">
          <motion.article initial={reduceMotion ? false : { y: 20 }} whileInView={{ y: 0 }} viewport={{ once: true, amount: 0.2 }} transition={{ duration: 0.5 }}><span className="landing-step-number">01 / FIND</span><h3>Spot shared misunderstandings</h3><p>Group similar incorrect answers to see where a class may be getting stuck.</p></motion.article>
          <motion.article initial={reduceMotion ? false : { y: 20 }} whileInView={{ y: 0 }} viewport={{ once: true, amount: 0.2 }} transition={{ duration: 0.5, delay: 0.08 }}><span className="landing-step-number">02 / VERIFY</span><h3>Read what students wrote</h3><p>Inspect the original responses and group support before accepting a proposed misconception.</p></motion.article>
          <motion.article initial={reduceMotion ? false : { y: 20 }} whileInView={{ y: 0 }} viewport={{ once: true, amount: 0.2 }} transition={{ duration: 0.5, delay: 0.16 }}><span className="landing-step-number">03 / RESPOND</span><h3>Keep the teacher in control</h3><p>Use your own material to ground a draft intervention, then edit and approve it yourself.</p></motion.article>
        </div>
      </section>
      <section className="landing-close"><div><p className="landing-overline">Ready to look beyond the score?</p><h2>Start with the students’ words.</h2></div><motion.button className="landing-action landing-action--light" onClick={onWorkspace} whileHover={hover} whileTap={reduceMotion ? undefined : { scale: 0.98 }}>Open teacher workspace <span aria-hidden="true">→</span></motion.button></section>
    </main>
    <footer className="landing-footer"><span>ClassLens</span><span>From grades to understanding.</span></footer>
  </div></MotionConfig>
}
