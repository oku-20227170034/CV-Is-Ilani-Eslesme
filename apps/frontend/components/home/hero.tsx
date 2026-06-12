'use client';

import React from 'react';
import Link from 'next/link';
import { useTranslations } from '@/lib/i18n';
import { ChevronRight } from 'lucide-react';

export default function Hero() {
  const { t } = useTranslations();

  return (
    <section className="relative min-h-screen w-full flex items-center justify-center overflow-hidden bg-rose-100">
      {/* Background Image with Overlay */}
      <div 
        className="absolute inset-0 bg-cover bg-center bg-no-repeat"
        style={{ 
          backgroundImage: 'url(/premium_hero_bg_1778012518822.png)',
          transform: 'scale(1.1)',
        }}
      >
        <div className="absolute inset-0 bg-gradient-to-b from-rose-900/20 via-rose-800/10 to-rose-50" />
      </div>

      {/* Decorative Blobs */}
      <div className="absolute top-1/4 -left-20 w-96 h-96 bg-primary/20 rounded-full blur-[120px] animate-pulse" />
      <div className="absolute bottom-1/4 -right-20 w-[500px] h-[500px] bg-rose-400/10 rounded-full blur-[150px] animate-pulse delay-700" />

      <div className="relative z-10 max-w-7xl mx-auto px-6 text-center">
        <h1 className="mb-12 text-center font-sans text-5xl md:text-7xl lg:text-[7rem] font-bold leading-[1.1] tracking-tighter text-rose-900 drop-shadow-xl">
          <span className="block opacity-90">ASOZ |</span>
          <span className="block italic text-white/95">CV EŞLEŞTİRME</span>
        </h1>

        <div className="flex flex-col sm:flex-row items-center justify-center gap-6 mt-12">
          <Link href="/dashboard" className="group relative px-20 py-8 bg-rose-900 text-white rounded-full font-bold text-2xl shadow-premium-xl transition-all duration-500 hover:bg-rose-800 hover:-translate-y-2 hover:shadow-2xl flex items-center gap-6 active:scale-95">
            {t('home.launchApp')}
            <ChevronRight className="w-8 h-8 transition-transform group-hover:translate-x-2" />
          </Link>
        </div>
      </div>
    </section>
  );
}
