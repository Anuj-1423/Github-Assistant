"use client";

import Link from "next/link";
import { useState, useEffect } from "react";

export default function LandingPage() {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 50);
    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  return (
    <div className="landing-page">
      {/* Navigation */}
      <nav className={`nav-bar ${scrolled ? 'scrolled' : ''}`}>
        <div className="container nav-container">
          <Link href="/" className="nav-logo">
            <div className="logo-box">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3"><path d="m18 16 4-4-4-4"/><path d="m6 8-4 4 4 4"/><path d="m14.5 4-5 16"/></svg>
            </div>
            <div>
               <div style={{ fontWeight: 900, fontSize: '24px', letterSpacing: '-0.06em' }}>CODE INTEL</div>
               <div style={{ fontSize: '9px', fontWeight: 700, color: 'var(--primary-brand)', letterSpacing: '0.3em', textTransform: 'uppercase' }}>Intelligence Engine</div>
            </div>
          </Link>
          
          <div className="nav-links">
            <Link href="/" className="nav-link active">Home</Link>
            <Link href="/features" className="nav-link">Features</Link>
            <Link href="/about" className="nav-link">About</Link>
            <Link href="/contact" className="nav-link">Contact</Link>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '32px' }}>
            <Link href="/login" className="nav-link" style={{ color: 'var(--text-secondary)' }}>Sign in</Link>
            <Link href="/dashboard" className="btn btn-primary" style={{ padding: '12px 24px', borderRadius: '12px', fontSize: '12px' }}>
              Launch Platform
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="section-padding flex-center" style={{ minHeight: '100vh', textAlign: 'center', position: 'relative', overflow: 'hidden' }}>
        <div className="hero-bg-orb" style={{ position: 'absolute', top: '0', left: '50%', transform: 'translateX(-50%)', width: '1000px', height: '600px', background: 'rgba(59, 130, 246, 0.1)', filter: 'blur(150px)', borderRadius: '50%', zIndex: 0 }}></div>
        
        <div className="container animate-fade-in-up" style={{ position: 'relative', zIndex: 1 }}>
          <div style={{ display: 'inline-flex', alignItems: 'center', gap: '12px', padding: '8px 16px', background: 'rgba(255,255,255,0.05)', border: '1px solid var(--border-subtle)', borderRadius: '999px', marginBottom: '40px' }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--primary-brand)', boxShadow: '0 0 10px var(--primary-brand)' }}></span>
            <span style={{ fontSize: '10px', fontWeight: 900, textTransform: 'uppercase', letterSpacing: '0.2em', color: 'var(--text-secondary)' }}>Next-Gen Repository Understanding</span>
          </div>
          
          <h1 style={{ fontSize: 'clamp(60px, 10vw, 120px)', marginBottom: '48px' }}>
            Your Codebase. <br/>
            <span className="text-gradient">Fully Mapped.</span>
          </h1>
          
          <p style={{ maxWidth: '800px', margin: '0 auto 64px', fontSize: '20px', color: 'var(--text-secondary)', fontWeight: 500 }}>
            Stop searching and start knowing. Code Intel creates a living, semantic map of your entire software architecture, visualizing every dependency and answering every "why" in real-time.
          </p>
          
          <div style={{ display: 'flex', gap: '24px', justifyContent: 'center' }}>
            <Link href="/dashboard" className="btn btn-primary" style={{ padding: '24px 48px', fontSize: '20px', borderRadius: '20px' }}>
              Get Started Free
            </Link>
            <Link href="/features" className="btn btn-secondary" style={{ padding: '24px 48px', fontSize: '20px', borderRadius: '20px' }}>
              View Features
            </Link>
          </div>
        </div>
      </section>

      {/* Bento Section */}
      <section className="section-padding" style={{ background: '#080808' }}>
        <div className="container">
          <div style={{ marginBottom: '80px' }}>
             <h2 style={{ fontSize: '48px', marginBottom: '24px' }}>Engineering <br/><span style={{ color: 'var(--text-muted)' }}>Superpowers.</span></h2>
             <p style={{ fontSize: '18px', color: 'var(--text-secondary)', maxWidth: '500px' }}>A suite of tools designed to eliminate cognitive load and accelerate the delivery of complex systems.</p>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(12, 1fr)', gap: '24px' }}>
             <div className="glass-panel" style={{ gridColumn: 'span 8', minHeight: '400px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
                <div>
                   <span style={{ color: 'var(--primary-brand)', fontSize: '12px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.2em', display: 'block', marginBottom: '16px' }}>Visual Analysis</span>
                   <h3 style={{ fontSize: '36px', marginBottom: '24px' }}>Interactive Dependency Graphs</h3>
                   <p style={{ color: 'var(--text-secondary)', fontSize: '18px', maxWidth: '400px' }}>Instantly visualize how files, classes, and functions relate. Click any node to see its entire logic chain across your repo.</p>
                </div>
                <div style={{ height: '160px', background: 'linear-gradient(to top, rgba(59, 130, 246, 0.2), transparent)', borderRadius: '24px 24px 0 0' }}></div>
             </div>

             <div className="glass-panel" style={{ gridColumn: 'span 4', textAlign: 'center', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
                <div style={{ fontSize: '60px', marginBottom: '32px' }}>🤖</div>
                <h3 style={{ fontSize: '24px', marginBottom: '16px' }}>Agentic Reasoning</h3>
                <p style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>LLM-powered agents that traverse your graph to explain architectural decisions.</p>
             </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer style={{ padding: '120px 0 80px', background: 'var(--canvas)', borderTop: '1px solid var(--border-subtle)' }}>
         <div className="container">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '80px' }}>
               <div className="nav-logo">
                  <div className="logo-box">C</div>
                  <h1 style={{ fontSize: '24px' }}>CODE INTEL</h1>
               </div>
               <div className="nav-links">
                  <Link href="/features" className="nav-link">Features</Link>
                  <Link href="/about" className="nav-link">About</Link>
                  <Link href="/contact" className="nav-link">Contact</Link>
                  <Link href="/dashboard" className="nav-link">App</Link>
               </div>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', borderTop: '1px solid var(--border-subtle)', paddingTop: '40px' }}>
               <p style={{ fontSize: '10px', fontWeight: 900, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.4em' }}>© 2026 Code Intelligence Systems.</p>
               <div style={{ display: 'flex', gap: '40px' }}>
                  <a href="#" className="nav-link" style={{ fontSize: '10px' }}>Privacy Policy</a>
                  <a href="#" className="nav-link" style={{ fontSize: '10px' }}>GDPR</a>
               </div>
            </div>
         </div>
      </footer>
    </div>
  );
}
