"use client";

import Link from "next/link";
import { useState } from "react";

export default function LoginPage() {
  const [isLogin, setIsLogin] = useState(true);

  return (
    <div className="min-h-screen bg-[#050505] text-white font-sans flex flex-col lg:flex-row overflow-hidden">
      {/* Branding Side (Lengthy/Professional Side) */}
      <div className="hidden lg:flex flex-1 bg-zinc-900/50 border-r border-white/5 relative items-center justify-center p-20 overflow-hidden">
         <div className="absolute top-0 left-0 w-full h-full bg-[radial-gradient(circle_at_center,_rgba(59,130,246,0.1)_0%,_transparent_70%)]"></div>
         <div className="relative z-10 max-w-lg">
            <Link href="/" className="flex items-center gap-4 mb-16 group">
               <div className="w-12 h-12 bg-primary-brand rounded-2xl flex items-center justify-center text-black font-black">
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3"><path d="m18 16 4-4-4-4"/><path d="m6 8-4 4 4 4"/><path d="m14.5 4-5 16"/></svg>
               </div>
               <h1 className="font-black tracking-tighter text-3xl">CODE INTEL</h1>
            </Link>
            <h2 className="text-5xl font-black tracking-tighter leading-tight mb-8">
               Empowering <br/><span className="text-zinc-500">Intelligence.</span>
            </h2>
            <p className="text-xl text-zinc-400 leading-relaxed font-medium mb-12">
               Join 50,000+ developers using Code Intel to master complex codebases and ship faster.
            </p>
            
            <div className="space-y-6">
               <div className="flex items-center gap-4">
                  <div className="w-2 h-2 rounded-full bg-primary-brand"></div>
                  <span className="text-sm font-bold text-zinc-300">Unified Repository Understanding</span>
               </div>
               <div className="flex items-center gap-4">
                  <div className="w-2 h-2 rounded-full bg-secondary-brand"></div>
                  <span className="text-sm font-bold text-zinc-300">Real-time dependency graphs</span>
               </div>
               <div className="flex items-center gap-4">
                  <div className="w-2 h-2 rounded-full bg-primary-brand"></div>
                  <span className="text-sm font-bold text-zinc-300">Enterprise-grade security</span>
               </div>
            </div>
         </div>
      </div>

      {/* Form Side */}
      <div className="flex-1 flex flex-col justify-center px-8 sm:px-20 lg:px-32 py-20 relative bg-black">
         <div className="max-w-md w-full mx-auto">
            <div className="mb-12">
               <h3 className="text-4xl font-black tracking-tighter mb-4">
                  {isLogin ? "Welcome back." : "Create Account."}
               </h3>
               <p className="text-zinc-500 font-medium">
                  {isLogin ? "Enter your credentials to access your dashboard." : "Start your 14-day free trial today."}
               </p>
            </div>

            <form className="space-y-6">
               {!isLogin && (
                  <div className="space-y-2">
                     <label className="text-[10px] font-black uppercase tracking-[0.3em] text-zinc-500 px-1">Full Name</label>
                     <input type="text" placeholder="John Doe" className="w-full bg-zinc-900 border border-white/10 rounded-2xl p-5 text-sm focus:outline-none focus:border-primary-brand transition-all" />
                  </div>
               )}
               <div className="space-y-2">
                  <label className="text-[10px] font-black uppercase tracking-[0.3em] text-zinc-500 px-1">Email Address</label>
                  <input type="email" placeholder="name@company.com" className="w-full bg-zinc-900 border border-white/10 rounded-2xl p-5 text-sm focus:outline-none focus:border-primary-brand transition-all" />
               </div>
               <div className="space-y-2">
                  <div className="flex items-center justify-between px-1">
                     <label className="text-[10px] font-black uppercase tracking-[0.3em] text-zinc-500">Password</label>
                     {isLogin && <a href="#" className="text-[10px] font-black uppercase tracking-[0.2em] text-primary-brand hover:underline">Forgot?</a>}
                  </div>
                  <input type="password" placeholder="••••••••" className="w-full bg-zinc-900 border border-white/10 rounded-2xl p-5 text-sm focus:outline-none focus:border-primary-brand transition-all" />
               </div>

               <Link href="/dashboard" className="block">
                  <button className="w-full py-5 bg-white text-black font-black text-xl rounded-2xl shadow-2xl transition-all hover:scale-[1.02] active:scale-95">
                     {isLogin ? "Sign In" : "Create Account"}
                  </button>
               </Link>

               <div className="relative py-4 flex items-center gap-4">
                  <div className="flex-1 h-[1px] bg-white/5"></div>
                  <span className="text-[10px] font-black uppercase tracking-widest text-zinc-700">or continue with</span>
                  <div className="flex-1 h-[1px] bg-white/5"></div>
               </div>

               <button type="button" className="w-full py-4 bg-zinc-900 border border-white/10 text-white font-bold text-sm rounded-2xl flex items-center justify-center gap-3 hover:bg-zinc-800 transition-all">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor"><path d="M12 .297c-6.63 0-12 5.373-12 12 0 5.303 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61C4.422 18.07 3.633 17.7 3.633 17.7c-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 22.092 24 17.592 24 12.297c0-6.627-5.373-12-12-12"/></svg>
                  GitHub
               </button>
            </form>

            <div className="mt-12 text-center">
               <p className="text-sm font-medium text-zinc-500">
                  {isLogin ? "Don't have an account?" : "Already have an account?"}
                  <button 
                    onClick={() => setIsLogin(!isLogin)}
                    className="ml-2 text-primary-brand font-black hover:underline uppercase tracking-widest text-[10px]"
                  >
                     {isLogin ? "Sign Up Now" : "Log In Now"}
                  </button>
               </p>
            </div>
         </div>
      </div>
    </div>
  );
}
