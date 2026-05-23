"use client";

import Link from "next/link";

export default function AboutPage() {
  return (
    <div className="about-page">
      <nav className="nav-bar scrolled">
        <div className="container nav-container">
          <Link href="/" className="nav-logo">
            <div className="logo-box">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3"><path d="m18 16 4-4-4-4"/><path d="m6 8-4 4 4 4"/><path d="m14.5 4-5 16"/></svg>
            </div>
            <h1 style={{ fontSize: '24px' }}>CODE INTEL</h1>
          </Link>
          <div className="nav-links">
            <Link href="/" className="nav-link">Home</Link>
            <Link href="/features" className="nav-link">Features</Link>
            <Link href="/about" className="nav-link active">About</Link>
            <Link href="/login" className="btn btn-primary" style={{ padding: '10px 24px', fontSize: '12px', borderRadius: '12px' }}>
              Login
            </Link>
          </div>
        </div>
      </nav>

      <section className="section-padding" style={{ position: 'relative', overflow: 'hidden' }}>
        <div className="container">
           <div style={{ maxWidth: '800px', marginBottom: '120px' }}>
              <span style={{ color: 'var(--primary-brand)', fontWeight: 900, textTransform: 'uppercase', letterSpacing: '0.4em', fontSize: '10px', display: 'block', marginBottom: '24px' }}>Our Mission</span>
              <h1 style={{ fontSize: 'clamp(48px, 8vw, 80px)', marginBottom: '48px' }}>
                We're mapping the <br/><span style={{ color: 'var(--text-muted)' }}>DNA of Software.</span>
              </h1>
              <p style={{ fontSize: '24px', color: 'var(--text-secondary)', fontWeight: 500 }}>
                Founded by engineers who were tired of getting lost in legacy codebases, Code Intel is building the definitive operating system for repository understanding.
              </p>
           </div>

           <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '80px', padding: '100px 0', borderTop: '1px solid var(--border-subtle)', borderBottom: '1px solid var(--border-subtle)' }}>
              <StatItem label="Files Indexed" value="10M+" />
              <StatItem label="Logic Nodes" value="500M+" />
              <StatItem label="Active Developers" value="50K+" />
           </div>

           <div style={{ padding: '160px 0', display: 'flex', flexDirection: 'column', gap: '120px' }}>
              <StoryBlock 
                title="The Cognitive Load Problem"
                content="As software systems grow, they exceed the limits of human memory. Developers spend 70% of their time reading and navigating code rather than writing it. We saw this as the single biggest bottleneck in human innovation."
              />
              <StoryBlock 
                title="Our Approach: Graph-First Intelligence"
                content="Unlike simple search tools, Code Intel treats your code as a living graph. By understanding the semantic relationships between every line, we provide a recursive context that mirrors the way senior architects think about systems."
              />
           </div>

           {/* Values Section */}
           <div style={{ padding: '160px 0', borderTop: '1px solid var(--border-subtle)' }}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '80px' }}>
                 <h2 style={{ fontSize: '48px' }}>Our Core <br/><span style={{ color: 'var(--text-muted)' }}>Values.</span></h2>
                 <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '48px' }}>
                    <ValueItem title="Radical Transparency" desc="We believe in showing exactly how our engine reaches its conclusions." />
                    <ValueItem title="Engineer-First" desc="Every feature must save a developer at least 30 minutes a day." />
                    <ValueItem title="Privacy by Design" desc="Your source code belongs to you. Always." />
                    <ValueItem title="Continuous Evolution" desc="Software is living; our maps must be living too." />
                 </div>
              </div>
           </div>
        </div>
      </section>

      <footer style={{ padding: '80px 0', borderTop: '1px solid var(--border-subtle)', textAlign: 'center' }}>
         <div className="container">
            <div style={{ fontWeight: 900, fontSize: '24px', marginBottom: '24px' }}>CODE INTEL</div>
            <p style={{ fontSize: '10px', fontWeight: 900, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.4em' }}>© 2026 Code Intelligence Systems.</p>
         </div>
      </footer>
    </div>
  );
}

function StatItem({ label, value }: any) {
  return (
    <div>
       <div style={{ fontSize: '48px', fontWeight: 900, letterSpacing: '-0.05em' }}>{value}</div>
       <div style={{ fontSize: '10px', fontWeight: 900, textTransform: 'uppercase', letterSpacing: '0.3em', color: 'var(--primary-brand)' }}>{label}</div>
    </div>
  );
}

function StoryBlock({ title, content }: any) {
  return (
    <div style={{ maxWidth: '800px' }}>
       <h3 style={{ fontSize: '36px', marginBottom: '32px' }}>{title}</h3>
       <p style={{ fontSize: '20px', color: 'var(--text-secondary)', lineHeight: '1.6' }}>{content}</p>
    </div>
  );
}

function ValueItem({ title, desc }: any) {
  return (
    <div>
       <h4 style={{ fontSize: '20px', marginBottom: '16px' }}>{title}</h4>
       <p style={{ fontSize: '14px', color: 'var(--text-secondary)', lineHeight: '1.6' }}>{desc}</p>
    </div>
  );
}
