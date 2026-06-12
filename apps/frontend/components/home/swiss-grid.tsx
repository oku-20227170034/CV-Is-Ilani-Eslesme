'use client';

import React from 'react';
import Image from 'next/image';
import Link from 'next/link';
import { useTranslations } from '@/lib/i18n';

export const SwissGrid = ({ children }: { children: React.ReactNode }) => {
  const { t } = useTranslations();

  return (
    <div
      className="min-h-screen w-full flex justify-center items-start py-4 px-4 md:py-8 md:px-8 overflow-hidden bg-rose-50"
    >
      {/* The Main Container */}
      <div className="w-full max-w-[90rem] min-h-[90vh] bg-rose-100/90 border border-rose-200 shadow-premium-xl flex flex-col overflow-hidden rounded-[2rem]">
        {/* Header Section */}
        <div className="p-8 md:p-10 shrink-0 bg-white/50 relative z-30 border-b border-rose-100">
          <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
            <div>
              <h1 className="font-serif text-5xl md:text-7xl text-rose-900 tracking-tighter leading-none">
                {t('nav.dashboard')}
              </h1>
              <p className="mt-4 text-sm font-medium text-rose-300/80 max-w-md">
                {t('dashboard.selectModule')}
              </p>
            </div>
            <div className="flex gap-4">
               {/* Stats or breadcrumbs could go here */}
            </div>
          </div>
        </div>

        {/* Content Grid */}
        <div className="@container flex-1 overflow-y-auto overflow-x-hidden relative z-10">
          <div className="p-6 md:p-8">
            <div className="grid grid-cols-1 @2xl:grid-cols-2 @3xl:grid-cols-3 @5xl:grid-cols-5 gap-6">
              {children}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="p-6 md:px-12 bg-white/60 flex justify-between items-center font-sans text-xs text-rose-400 border-t border-rose-100 shrink-0 relative z-30">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-primary rounded-lg">
              <Image
                src="/logo.svg"
                alt="Resume Matcher"
                width={16}
                height={16}
                className="w-4 h-4 brightness-0 invert"
              />
            </div>
            <span className="uppercase font-bold tracking-widest text-rose-900">ASOZ | CV Eşleştirme</span>
          </div>
          <div className="flex items-center gap-4">
            <Link
              href="/settings"
              className="bg-white text-rose-900 border border-rose-200 px-8 py-3 rounded-full uppercase font-bold tracking-widest shadow-premium-sm hover:bg-primary hover:text-white hover:border-primary hover:-translate-y-0.5 transition-all min-w-[160px] text-center active:scale-95"
            >
              {t('nav.settings')}
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
};
