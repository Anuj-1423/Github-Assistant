"use client";

import Link from "next/link";

export default function ContactPage() {
  return (
    <div className="contact-page">
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
            <Link href="/about" className="nav-link">About</Link>
            <Link href="/login" className="btn btn-primary" style={{ padding: '10px 24px', fontSize: '12px', borderRadius: '12px' }}>
              Login
            </Link>
          </div>
        </div>
      </nav>

      <section className="section-padding">
        <div className="container">
           <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '120px' }}>
              <div>
                 <h1 style={{ fontSize: 'clamp(48px, 8vw, 80px)', marginBottom: '40px' }}>
                   Let's talk <br/><span style={{ color: 'var(--text-muted)' }}>Intelligence.</span>
                 </h1>
                 <p style={{ fontSize: '20px', color: 'var(--text-secondary)', marginBottom: '80px', lineHeight: '1.6' }}>
                   Whether you have a technical question or want a custom demo for your enterprise team, we're here to help.
                 </p>

                 <div style={{ display: 'flex', flexDirection: 'column', gap: '64px' }}>
                    <ContactDetail 
                       title="Technical Support"
                       detail="support@codeintel.ai"
                       desc="Available 24/7 for Enterprise customers."
                    />
                    <ContactDetail 
                       title="Sales Inquiries"
                       detail="sales@codeintel.ai"
                       desc="Tailored pricing for high-growth teams."
                    />
                    <ContactDetail 
                       title="Global Headquarters"
                       detail="San Francisco, CA"
                       desc="101 Mission St, Financial District."
                    />
                 </div>
              </div>

              <div className="glass-panel" style={{ padding: '64px' }}>
                 <form style={{ display: 'flex', flexDirection: 'column', gap: '32px' }}>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
                       <div className="form-group">
                          <label className="form-label">First Name</label>
                          <input type="text" className="form-input" placeholder="John" />
                       </div>
                       <div className="form-group">
                          <label className="form-label">Last Name</label>
                          <input type="text" className="form-input" placeholder="Doe" />
                       </div>
                    </div>

                    <div className="form-group">
                       <label className="form-label">Work Email</label>
                       <input type="email" className="form-input" placeholder="john@company.com" />
                    </div>

                    <div className="form-group">
                       <label className="form-label">How can we help?</label>
                       <textarea className="form-input" rows={6} placeholder="Describe your challenge..."></textarea>
                    </div>

                    <button className="btn btn-primary" style={{ padding: '20px' }}>Send Message</button>
                 </form>
              </div>
           </div>
        </div>
      </section>

      {/* SLA Tiers section using Vanilla CSS */}
      <section className="section-padding" style={{ borderTop: '1px solid var(--border-subtle)', background: 'var(--surface)' }}>
         <div className="container">
            <h2 style={{ fontSize: '48px', textAlign: 'center', marginBottom: '80px' }}>Support <span style={{ color: 'var(--text-muted)' }}>Tiers.</span></h2>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '40px' }}>
               <TierCard title="Developer" resp="Community" access="Docs & Forums" />
               <TierCard title="Business" resp="< 12 Hours" access="Email & Slack" active />
               <TierCard title="Enterprise" resp="< 1 Hour" access="Dedicated Phone" />
            </div>
         </div>
      </section>

      <footer style={{ padding: '80px 0', borderTop: '1px solid var(--border-subtle)', textAlign: 'center' }}>
         <div className="container">
            <div style={{ fontWeight: 900, fontSize: '24px', marginBottom: '24px' }}>CODE INTEL</div>
            <div style={{ display: 'flex', justifyContent: 'center', gap: '40px', fontSize: '12px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.2em' }}>
               <Link href="/" className="nav-link">Home</Link>
               <Link href="/features" className="nav-link">Features</Link>
               <Link href="/about" className="nav-link">About</Link>
               <Link href="/dashboard" className="nav-link">App</Link>
            </div>
         </div>
      </footer>

      <style jsx>{`
        .form-group {
          display: flex;
          flex-direction: column;
          gap: 12px;
        }
        .form-label {
          font-size: 10px;
          font-weight: 900;
          text-transform: uppercase;
          letter-spacing: 0.2em;
          color: var(--text-muted);
        }
        .form-input {
          background: rgba(0,0,0,0.5);
          border: 1px solid var(--border-subtle);
          border-radius: 12px;
          padding: 16px;
          color: white;
          font-family: inherit;
          font-size: 14px;
        }
        .form-input:focus {
          outline: none;
          border-color: var(--primary-brand);
        }
      `}</style>
    </div>
  );
}

function ContactDetail({ title, detail, desc }: any) {
  return (
    <div>
       <div style={{ fontSize: '10px', fontWeight: 900, textTransform: 'uppercase', letterSpacing: '0.3em', color: 'var(--primary-brand)', marginBottom: '8px' }}>{title}</div>
       <div style={{ fontSize: '24px', fontWeight: 900, marginBottom: '8px' }}>{detail}</div>
       <div style={{ fontSize: '14px', color: 'var(--text-secondary)' }}>{desc}</div>
    </div>
  );
}

function TierCard({ title, resp, access, active = false }: any) {
  return (
    <div className="glass-panel" style={{ border: active ? '1px solid var(--primary-brand)' : '1px solid var(--border-subtle)', background: active ? 'rgba(59, 130, 246, 0.05)' : 'rgba(255,255,255,0.03)' }}>
       <h4 style={{ fontSize: '12px', fontWeight: 900, textTransform: 'uppercase', letterSpacing: '0.2em', marginBottom: '32px' }}>{title}</h4>
       <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          <div>
             <div style={{ fontSize: '10px', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '4px' }}>Response Time</div>
             <div style={{ fontSize: '18px', fontWeight: 900 }}>{resp}</div>
          </div>
          <div>
             <div style={{ fontSize: '10px', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '4px' }}>Access Channel</div>
             <div style={{ fontSize: '18px', fontWeight: 900 }}>{access}</div>
          </div>
       </div>
    </div>
  );
}
