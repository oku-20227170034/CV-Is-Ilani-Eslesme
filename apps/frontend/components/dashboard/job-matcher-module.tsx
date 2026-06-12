"use client";

import React, { useState, useRef } from 'react';
import { useTranslations } from '@/lib/i18n';
import { Button } from '@/components/ui/button';
import { Card, CardTitle, CardDescription } from '@/components/ui/card';
import { Dialog, DialogContent, DialogTrigger, DialogTitle, DialogHeader } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Loader2, Search, Briefcase, FileText, FileUp, AlertCircle, CheckCircle2, ChevronDown, ChevronUp, ExternalLink } from 'lucide-react';
import { apiPost, apiFetch } from '@/lib/api/client';

interface JobMatchResult {
  baslik: string;
  sirket: string;
  lokasyon: string;
  link: string;
  ilan_no: string;
  uyum_skoru: number;
  eksik_yetkinlikler: string[];
  cv_onerileri: string[];
  aciklama: string;
  skor_aciklamasi?: string;
  eslesen_beceriler?: string[];
  maksimum_ulasabilir_skor?: number;
  cinsiyet?: string;
  yas?: string;
  deneyim?: string;
  calisma_sekli?: string;
  egitim?: string;
}

export function JobMatcherModule() {
  const { t } = useTranslations();
  const [isOpen, setIsOpen] = useState(false);
  const [tab, setTab] = useState<'paste' | 'upload'>('paste');
  const [position, setPosition] = useState('');
  const [cvText, setCvText] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [results, setResults] = useState<JobMatchResult[]>([]);
  const [error, setError] = useState('');
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isUploading, setIsUploading] = useState(false);

  const formatBadge = (label: string, value: string) => {
    if (!value) return '';
    const lowerValue = value.toLowerCase();
    const lowerLabel = label.toLowerCase();
    if (lowerValue.startsWith(lowerLabel)) return value;
    if (lowerValue === 'belirtilmemis' || lowerValue === 'belirtilmemiş') return `${label}: Belirtilmemiş`;
    return `${label}: ${value}`;
  };

  const handleAnalyze = async () => {
    if (!cvText.trim() || !position.trim()) return;
    
    setIsLoading(true);
    setError('');
    setResults([]);
    
    try {
      const response = await apiPost('/job-matcher/analyze', { cv_text: cvText, position });
      
      if (!response.ok) {
        throw new Error('Analysis failed');
      }
      
      const data = await response.json();
      setResults(data.matches || []);
    } catch (err) {
      console.error(err);
      setError(t('jobMatcher.errorOccurred'));
    } finally {
      setIsLoading(false);
    }
  };

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    setError('');

    const formData = new FormData();
    formData.append('file', file);
    let resumeId: string | null = null;

    try {
      // 1. Upload
      const response = await apiFetch('/resumes/upload', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || t('jobMatcher.errors.uploadFailed'));
      }

      const uploadData = await response.json();
      resumeId = uploadData.resume_id;

      // 2. Poll for content to become available
      let attempts = 0;
      const maxAttempts = 15;
      let extractedText = '';

      while (attempts < maxAttempts) {
        const fetchRes = await apiFetch(`/resumes?resume_id=${resumeId}`);
        if (fetchRes.ok) {
          const fetchData = await fetchRes.json();
          const status = fetchData.data.raw_resume.processing_status;
          const content = fetchData.data.raw_resume.content;

          if ((status === 'ready' || status === 'failed') && content) {
            extractedText = content;
            break;
          } else if (status === 'failed' && !content) {
            throw new Error(t('jobMatcher.errors.readFailed'));
          }
        } else {
          const errorData = await fetchRes.json().catch(() => ({}));
          throw new Error(errorData.detail || t('jobMatcher.errors.fetchFailed'));
        }

        attempts++;
        await new Promise(resolve => setTimeout(resolve, 1500));
      }

      if (!extractedText) {
        throw new Error(t('jobMatcher.errors.timeout'));
      }

      // 3. Set the text in the UI
      setCvText(extractedText);
      setTab('paste');

    } catch (err: any) {
      console.error(err);
      setError(err.message || t('jobMatcher.errors.generic'));
    } finally {
      // 4. Always delete the temporary resume record from the database
      if (resumeId) {
        apiFetch(`/resumes/${resumeId}`, { method: 'DELETE' }).catch(() => {
          // Silme başarısız olsa bile UI'yi engelleme
        });
      }
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-rose-600 bg-rose-50 border-rose-100';
    if (score >= 50) return 'text-amber-600 bg-amber-50 border-amber-100';
    return 'text-rose-400 bg-rose-50/50 border-rose-100/50';
  };

  const getScoreBarColor = (score: number) => {
    if (score >= 80) return 'bg-rose-500';
    if (score >= 50) return 'bg-amber-400';
    return 'bg-rose-300';
  };

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger asChild>
        <Card variant="interactive" className="aspect-square h-full hover:bg-primary hover:text-white cursor-pointer group rounded-2xl">
          <div className="flex-1 flex flex-col justify-center pointer-events-none p-6 h-full text-center">
            <CardTitle className="text-2xl font-serif font-bold group-hover:text-white transition-colors leading-[1.2]">
              {t('jobMatcher.title')}
            </CardTitle>
          </div>
        </Card>
      </DialogTrigger>
      
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto p-0 border-0 bg-transparent shadow-none">
        <DialogTitle className="sr-only">{t('jobMatcher.title')}</DialogTitle>
        <Card className="overflow-hidden border-none shadow-premium-xl bg-gradient-to-br from-rose-50 via-white to-rose-50/30 backdrop-blur-xl relative group rounded-3xl">
          {/* Decorative gradient blob */}
          <div className="absolute top-0 right-0 w-64 h-64 bg-primary/20 rounded-full blur-3xl -mr-32 -mt-32 pointer-events-none transition-all duration-700 group-hover:bg-primary/30" />
          
          <div className="p-8 relative z-10">
            <div className="flex items-center gap-4 mb-4">
              <div className="p-3 bg-gradient-to-br from-primary to-rose-500 text-white rounded-2xl shadow-premium-md">
                <Search className="w-6 h-6" />
              </div>
              <div>
                <h2 className="text-3xl font-serif font-bold bg-clip-text text-transparent bg-gradient-to-r from-rose-700 to-rose-900">
                  {t('jobMatcher.title')}
                </h2>
                <p className="text-rose-400 font-medium">{t('jobMatcher.subtitle')}</p>
              </div>
            </div>

        <div className="space-y-6">
          <div className="flex flex-col gap-2">
            <label className="text-sm font-semibold text-rose-800 uppercase tracking-widest ml-1">{t('jobMatcher.positionLabel')}</label>
            <Input 
              value={position}
              onChange={(e) => setPosition(e.target.value)}
              placeholder={t('jobMatcher.positionPlaceholder')}
              className="text-lg py-7 border-rose-100 focus-visible:ring-primary rounded-2xl bg-white/80 shadow-premium-sm"
            />
          </div>

          <div className="bg-white/60 rounded-2xl p-1 border border-slate-200 shadow-sm">
            <div className="flex gap-1 mb-4 p-1.5 bg-rose-50/50 rounded-2xl">
              <button
                onClick={() => setTab('paste')}
                className={`flex-1 py-3 text-sm font-bold rounded-xl transition-all flex items-center justify-center gap-2 ${tab === 'paste' ? 'bg-white text-rose-700 shadow-premium-sm' : 'text-rose-400 hover:text-rose-600 hover:bg-white/50'}`}
              >
                <FileText className="w-4 h-4" /> {t('jobMatcher.tabs.paste')}
              </button>
              <button
                onClick={() => setTab('upload')}
                className={`flex-1 py-3 text-sm font-bold rounded-xl transition-all flex items-center justify-center gap-2 ${tab === 'upload' ? 'bg-white text-rose-700 shadow-premium-sm' : 'text-rose-400 hover:text-rose-600 hover:bg-white/50'}`}
              >
                <FileUp className="w-4 h-4" /> {t('jobMatcher.tabs.upload')}
              </button>
            </div>

            {tab === 'paste' ? (
              <div className="p-2">
                <Textarea 
                  value={cvText}
                  onChange={(e) => setCvText(e.target.value)}
                  placeholder={t('jobMatcher.pasteArea.placeholder')}
                  className="min-h-[160px] resize-none border-slate-200 focus-visible:ring-indigo-500 rounded-xl"
                />
              </div>
            ) : (
              <div 
                onClick={() => !isUploading && fileInputRef.current?.click()}
                className={`p-8 border-2 border-dashed border-slate-300 hover:border-indigo-400 bg-slate-50/50 rounded-xl transition-colors flex flex-col items-center justify-center gap-3 text-center group cursor-pointer m-2 ${isUploading ? 'opacity-50 cursor-wait' : ''}`}
              >
                <input 
                  type="file" 
                  ref={fileInputRef} 
                  className="hidden" 
                  accept=".pdf,.docx,.doc" 
                  onChange={handleFileUpload}
                />
                <div className="p-5 bg-rose-50 text-rose-500 rounded-full group-hover:scale-110 group-hover:bg-primary group-hover:text-white transition-all duration-300">
                  {isUploading ? (
                    <Loader2 className="w-8 h-8 animate-spin" />
                  ) : (
                    <FileUp className="w-8 h-8" />
                  )}
                </div>
                <div>
                  <p className="font-bold text-rose-900 text-lg">
                    {isUploading ? t('jobMatcher.uploadArea.loading') : t('jobMatcher.uploadArea.title')}
                  </p>
                  <p className="text-sm text-rose-400 mt-1">{t('jobMatcher.uploadArea.subtitle')}</p>
                </div>
              </div>
            )}
          </div>

          <Button 
            onClick={handleAnalyze} 
            disabled={isLoading || isUploading || !cvText.trim() || !position.trim()}
            className="w-full py-8 text-xl rounded-2xl bg-gradient-to-r from-primary to-rose-500 hover:from-rose-500 hover:to-rose-600 text-white shadow-premium-lg transition-all active:scale-[0.98] font-serif"
          >
            {isLoading ? (
              <>
                <Loader2 className="mr-2 h-6 w-6 animate-spin" />
                {t('jobMatcher.analyzing')}
              </>
            ) : isUploading ? (
              <>
                <Loader2 className="mr-2 h-6 w-6 animate-spin" />
                {t('jobMatcher.uploadArea.loading')}
              </>
            ) : (
              <>
                <Briefcase className="mr-2 h-6 w-6" />
                {t('jobMatcher.analyzeButton')}
              </>
            )}
          </Button>

          {error && (
            <div className="p-4 bg-rose-50 text-rose-600 rounded-xl flex items-start gap-3 border border-rose-100">
              <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" />
              <p className="font-medium">{error}</p>
            </div>
          )}

          {results.length > 0 && (
            <div className="mt-10 pt-8 border-t border-rose-100">
              <h3 className="text-2xl font-serif font-bold text-rose-900 mb-6">{t('jobMatcher.resultsTitle')}</h3>
              <div className="space-y-6">
                {results.map((res, idx) => {
                  const isExpanded = expandedId === res.ilan_no;
                  return (
                    <div key={idx} className="bg-white border border-rose-100 rounded-3xl overflow-hidden shadow-premium-sm hover:shadow-premium-md transition-all duration-300">
                      <div className="p-6">
                        <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
                          <div>
                            <h4 className="text-xl font-serif font-bold text-foreground leading-tight">{res.baslik}</h4>
                            <p className="text-primary font-bold mt-1 text-lg">{res.sirket}</p>
                            <p className="text-sm text-rose-400 mt-2 flex items-center gap-2 font-medium">
                              {res.lokasyon} • {t('jobMatcher.ilanNo', { no: res.ilan_no })}
                            </p>
                          </div>
                          
                          <div className="flex flex-col items-end shrink-0">
                            <div className={`px-3 py-1.5 rounded-lg border font-bold flex items-center gap-1.5 ${getScoreColor(res.uyum_skoru)}`}>
                              <span className="text-lg">{res.uyum_skoru}%</span>
                              <span className="text-xs uppercase tracking-wider opacity-80">{t('jobMatcher.matchScore')}</span>
                            </div>
                          </div>
                        </div>

                        {/* Progress Bar */}
                        <div className="w-full bg-slate-100 h-2 rounded-full mt-4 overflow-hidden">
                          <div 
                            className={`h-full rounded-full transition-all duration-1000 ${getScoreBarColor(res.uyum_skoru)}`}
                            style={{ width: `${res.uyum_skoru}%` }}
                          />
                        </div>

                        {/* Quick Action Bar */}
                        <div className="flex items-center justify-between mt-6 pt-5 border-t border-rose-50">
                          <button 
                            onClick={() => setExpandedId(isExpanded ? null : res.ilan_no)}
                            className="text-sm font-bold text-rose-400 hover:text-primary flex items-center gap-2 transition-colors"
                          >
                            {isExpanded ? (
                              <><ChevronUp className="w-4 h-4" /> {t('jobMatcher.hideDetails')}</>
                            ) : (
                              <><ChevronDown className="w-4 h-4" /> {t('jobMatcher.showDetails')}</>
                            )}
                          </button>
                          
                          <a 
                            href={res.link} 
                            target="_blank" 
                            rel="noopener noreferrer"
                            className="text-sm font-bold text-white bg-gradient-to-r from-primary to-rose-400 hover:from-rose-400 hover:to-rose-500 px-6 py-2.5 rounded-full flex items-center gap-2 transition-all shadow-premium-sm active:scale-95"
                          >
                            {t('jobMatcher.applyNow')} <ExternalLink className="w-4 h-4" />
                          </a>
                        </div>
                      </div>

                      {/* Expanded Content */}
                      {isExpanded && (
                        <div className="p-6 bg-rose-50/20 border-t border-rose-50 space-y-8">
                          <div>
                            <p className="text-sm text-foreground/80 leading-relaxed bg-white/80 p-5 rounded-2xl border border-rose-100 shadow-premium-sm whitespace-pre-wrap">
                              {res.aciklama}
                            </p>
                            
                            {/* Tags / Details */}
                            <div className="flex flex-wrap gap-2 mt-4">
                              {res.deneyim && <span className="px-3 py-1.5 bg-white text-rose-700 text-xs font-bold rounded-full border border-rose-100 shadow-premium-sm">{formatBadge(t('jobMatcher.tags.experience'), res.deneyim)}</span>}
                              {res.calisma_sekli && <span className="px-3 py-1.5 bg-white text-rose-700 text-xs font-bold rounded-full border border-rose-100 shadow-premium-sm">{formatBadge(t('jobMatcher.tags.workType'), res.calisma_sekli)}</span>}
                              {res.egitim && <span className="px-3 py-1.5 bg-white text-rose-700 text-xs font-bold rounded-full border border-rose-100 shadow-premium-sm">{formatBadge(t('jobMatcher.tags.education'), res.egitim)}</span>}
                              {res.yas && <span className="px-3 py-1.5 bg-white text-rose-700 text-xs font-bold rounded-full border border-rose-100 shadow-premium-sm">{formatBadge(t('jobMatcher.tags.age'), res.yas)}</span>}
                              {res.cinsiyet && <span className="px-3 py-1.5 bg-white text-rose-700 text-xs font-bold rounded-full border border-rose-100 shadow-premium-sm">{formatBadge(t('jobMatcher.tags.gender'), res.cinsiyet)}</span>}
                            </div>
                          </div>

                          {/* Skor Açıklaması */}
                          {res.skor_aciklamasi && (
                            <div className="bg-white p-5 rounded-2xl border border-primary/20 flex gap-4 items-start shadow-premium-sm">
                              <span className="text-2xl mt-0.5">✨</span>
                              <div>
                                <p className="text-xs font-bold text-primary uppercase tracking-widest mb-1">{t('jobMatcher.scoreExplanation')}</p>
                                <p className="text-sm text-foreground font-medium">{res.skor_aciklamasi}</p>
                                {res.maksimum_ulasabilir_skor && (
                                  <p className="text-xs text-rose-400 mt-2 font-bold">{t('jobMatcher.potentialScore', { score: res.maksimum_ulasabilir_skor })}</p>
                                )}
                              </div>
                            </div>
                          )}

                          {/* Eşleşen Beceriler */}
                          <div className="bg-emerald-50/60 p-4 rounded-xl border border-emerald-100">
                            <h5 className="text-sm font-bold text-emerald-800 uppercase tracking-wider mb-3 flex items-center gap-2">
                              <CheckCircle2 className="w-4 h-4" /> {t('jobMatcher.matchingSkills')}
                            </h5>
                            {res.eslesen_beceriler && res.eslesen_beceriler.length > 0 ? (
                              <div className="flex flex-wrap gap-2">
                                {res.eslesen_beceriler.map((skill, i) => (
                                  <span key={i} className="px-2.5 py-1 bg-emerald-100 text-emerald-700 text-xs font-semibold rounded-md border border-emerald-200">
                                    ✓ {skill}
                                  </span>
                                ))}
                              </div>
                            ) : (
                              <p className="text-sm text-emerald-700 font-medium">{t('jobMatcher.noMatchingSkills')}</p>
                            )}
                          </div>

                          <div className="grid sm:grid-cols-2 gap-6">
                            {res.eksik_yetkinlikler?.length > 0 && (
                              <div className="bg-white p-5 rounded-2xl border border-rose-100 shadow-premium-sm">
                                <h5 className="text-xs font-bold text-rose-800 uppercase tracking-widest mb-4 flex items-center gap-2">
                                  <AlertCircle className="w-4 h-4" /> {t('jobMatcher.missingSkills')}
                                </h5>
                                <ul className="space-y-3">
                                  {res.eksik_yetkinlikler.map((skill, i) => (
                                    <li key={i} className="text-sm text-foreground/80 flex items-start gap-3 font-medium">
                                      <span className="mt-1.5 block w-1.5 h-1.5 rounded-full bg-rose-300 shrink-0" />
                                      {skill}
                                    </li>
                                  ))}
                                </ul>
                              </div>
                            )}

                            {res.cv_onerileri?.length > 0 && (
                              <div className="bg-white p-5 rounded-2xl border border-primary/10 shadow-premium-sm">
                                <h5 className="text-xs font-bold text-primary uppercase tracking-widest mb-4 flex items-center gap-2">
                                  <CheckCircle2 className="w-4 h-4" /> {t('jobMatcher.cvSuggestions')}
                                </h5>
                                <ul className="space-y-3">
                                  {res.cv_onerileri.map((sug, i) => (
                                    <li key={i} className="text-sm text-foreground/80 flex items-start gap-3 font-medium">
                                      <span className="mt-1.5 block w-1.5 h-1.5 rounded-full bg-primary/40 shrink-0" />
                                      {sug}
                                    </li>
                                  ))}
                                </ul>
                              </div>
                            )}
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      </div>
    </Card>
      </DialogContent>
    </Dialog>
  );
}
