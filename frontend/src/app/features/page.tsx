"use client";

import Link from "next/link";

export default function FeaturesPage() {
  return (
    <div className="features-page">
      {/* Shared Nav */}
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
            <Link href="/features" className="nav-link active">Features</Link>
            <Link href="/about" className="nav-link">About</Link>
            <Link href="/login" className="btn btn-primary" style={{ padding: '10px 24px', fontSize: '12px', borderRadius: '12px' }}>
              Login
            </Link>
          </div>
        </div>
      </nav>

      <section className="section-padding">
        <div className="container">
          <div style={{ maxWidth: '800px' }}>
            <span style={{ color: 'var(--primary-brand)', fontWeight: 900, textTransform: 'uppercase', letterSpacing: '0.4em', fontSize: '10px', display: 'block', marginBottom: '24px' }}>Capability Matrix</span>
            <h1 style={{ fontSize: 'clamp(48px, 8vw, 80px)', marginBottom: '40px' }}>
              The Engine of <br/><span style={{ color: 'var(--text-muted)' }}>Understanding.</span>
            </h1>
            <p style={{ fontSize: '20px', color: 'var(--text-secondary)', lineHeight: '1.6' }}>
              We've dismantled the traditional code search and rebuilt it from the ground up using graph theory and semantic intelligence.
            </p>
          </div>
        </div>
      </section>

      <section className="section-padding" style={{ borderTop: '1px solid var(--border-subtle)' }}>
        <div className="container" style={{ display: 'flex', flexDirection: 'column', gap: '160px' }}>
           <FeatureRow 
              num="01"
              title="Semantic Relationship Mapping"
              desc="Traditional search finds text. We find meaning. Our engine builds a multi-dimensional map of your codebase, identifying how a function in your auth service impacts a class in your payment gateway."
              image="🔍"
           />
           <FeatureRow 
              num="02"
              title="Agentic Architectural Reasoning"
              desc="When you ask 'How does checkout work?', our system doesn't just show you code. An autonomous agent traverses the dependency graph and synthesizes a high-level architectural explanation."
              image="🤖"
              reverse
           />
           <FeatureRow 
              num="03"
              title="Interactive Flow Explorer"
              desc="Visualize the journey of data through your system. Our interactive graph allows you to trace call chains, identify bottlenecks, and see precisely where logic is distributed."
              image="🕸️"
           />
        </div>
      </section>

      {/* Workflow Section */}
      <section className="section-padding" style={{ background: 'var(--surface)', borderTop: '1px solid var(--border-subtle)', borderBottom: '1px solid var(--border-subtle)' }}>
         <div className="container">
            <h2 style={{ fontSize: '48px', textAlign: 'center', marginBottom: '100px' }}>How it <span style={{ color: 'var(--text-muted)' }}>Works.</span></h2>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '48px' }}>
               <StepItem num="1" title="Connect" desc="Link your GitHub, GitLab, or local directory in seconds." />
               <StepItem num="2" title="Index" desc="Our engine parses every AST node and builds a semantic vector space." />
               <StepItem num="3" title="Map" desc="Relationships are extracted and a dependency graph is materialized." />
               <StepItem num="4" title="Reason" desc="Ask any question and our agent will traverse the graph for answers." />
            </div>
         </div>
      </section>

      {/* CTA Section */}
      <section className="section-padding" style={{ background: 'var(--primary-brand)', color: 'black', textAlign: 'center' }}>
         <div className="container">
            <h2 style={{ fontSize: '64px', marginBottom: '32px' }}>Ready to master your <br/>codebase?</h2>
            <p style={{ fontSize: '20px', fontWeight: 700, marginBottom: '64px', opacity: 0.7, maxWidth: '700px', margin: '0 auto 64px' }}>Join the future of software intelligence. Start your free trial today or talk to an expert about enterprise deployment.</p>
            <div style={{ display: 'flex', justifyContent: 'center', gap: '24px' }}>
               <Link href="/login" className="btn btn-primary" style={{ background: 'black', color: 'white', padding: '24px 48px', fontSize: '20px', borderRadius: '20px' }}>
                  Sign Up Now
               </Link>
               <Link href="/contact" className="btn" style={{ border: '4px solid black', padding: '24px 48px', fontSize: '20px', borderRadius: '20px' }}>
                  Contact Sales
               </Link>
            </div>
         </div>
      </section>

      <footer style={{ padding: '80px 0', borderTop: '1px solid var(--border-subtle)', textAlign: 'center' }}>
         <div className="container">
            <div style={{ fontWeight: 900, letterSpacing: '-0.05em', fontSize: '24px', marginBottom: '24px' }}>CODE INTEL</div>
            <div style={{ display: 'flex', justifyContent: 'center', gap: '40px', fontSize: '12px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.2em' }}>
               <Link href="/" className="nav-link">Home</Link>
               <Link href="/about" className="nav-link">About</Link>
               <Link href="/contact" className="nav-link">Contact</Link>
               <Link href="/dashboard" className="nav-link">App</Link>
            </div>
         </div>
      </footer>
    </div>
  );
}

function FeatureRow({ num, title, desc, image, reverse = false }: any) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '80px', flexDirection: reverse ? 'row-reverse' : 'row' }}>
       <div style={{ flex: 1 }}>
          <div style={{ fontSize: '64px', color: 'var(--surface-accent)', marginBottom: '32px' }}>{num}</div>
          <h2 style={{ fontSize: '36px', marginBottom: '24px' }}>{title}</h2>
          <p style={{ fontSize: '18px', color: 'var(--text-secondary)', lineHeight: '1.6', marginBottom: '32px' }}>{desc}</p>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
             {["AST Parsing", "Vector Indexing", "Cross-Service", "Real-time"].map((t, i) => (
               <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '12px', fontSize: '12px', fontWeight: 700, color: 'var(--text-muted)' }}>
                  <div style={{ width: '6px', height: '6px', borderRadius: '50%', background: 'var(--primary-brand)' }}></div>
                  {t}
               </div>
             ))}
          </div>
       </div>
       <div className="glass-panel" style={{ flex: 1, height: '400px', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '120px' }}>
          {image}
       </div>
    </div>
  );
}

function StepItem({ num, title, desc }: any) {
  return (
    <div style={{ textAlign: 'left' }}>
       <div className="flex-center" style={{ width: '48px', height: '48px', borderRadius: '50%', border: '1px solid var(--border-subtle)', marginBottom: '24px', fontWeight: 900 }}>{num}</div>
       <h4 style={{ fontSize: '20px', marginBottom: '16px' }}>{title}</h4>
       <p style={{ fontSize: '14px', color: 'var(--text-secondary)' }}>{desc}</p>
    </div>
  );
}
