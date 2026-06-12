'use client';

import { SwissGrid } from '@/components/home/swiss-grid';
import { JobMatcherModule } from '@/components/dashboard/job-matcher-module';
import { ResumeUploadDialog } from '@/components/dashboard/resume-upload-dialog';
import { useState, useEffect, useCallback, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { ConfirmDialog } from '@/components/ui/confirm-dialog';
import { Card, CardTitle, CardDescription } from '@/components/ui/card';
import Link from 'next/link';
import { useTranslations } from '@/lib/i18n';

// Optimized Imports for Performance (No Barrel Imports)
import Loader2 from 'lucide-react/dist/esm/icons/loader-2';
import AlertCircle from 'lucide-react/dist/esm/icons/alert-circle';
import RefreshCw from 'lucide-react/dist/esm/icons/refresh-cw';
import Plus from 'lucide-react/dist/esm/icons/plus';
import Settings from 'lucide-react/dist/esm/icons/settings';
import AlertTriangle from 'lucide-react/dist/esm/icons/alert-triangle';

import {
  fetchResume,
  fetchResumeList,
  deleteResume,
  retryProcessing,
  fetchJobDescription,
  type ResumeListItem,
} from '@/lib/api/resume';
import { useStatusCache } from '@/lib/context/status-cache';

type ProcessingStatus = 'pending' | 'processing' | 'ready' | 'failed' | 'loading';

export default function DashboardPage() {
  const { t, locale } = useTranslations();
  const [masterResumeId, setMasterResumeId] = useState<string | null>(null);
  const [processingStatus, setProcessingStatus] = useState<ProcessingStatus>('loading');
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [tailoredResumes, setTailoredResumes] = useState<ResumeListItem[]>([]);
  const [isRetrying, setIsRetrying] = useState(false);
  const [isUploadDialogOpen, setIsUploadDialogOpen] = useState(false);
  const router = useRouter();

  // Status cache for optimistic counter updates and LLM status check
  const {
    status: systemStatus,
    isLoading: statusLoading,
    incrementResumes,
    decrementResumes,
    setHasMasterResume,
  } = useStatusCache();

  // Request id guard for concurrent loadTailoredResumes invocations
  const loadRequestIdRef = useRef(0);
  // Lightweight in-memory cache for job snippets to avoid N+1 refetches
  const jobSnippetCacheRef = useRef<Record<string, string>>({});

  // Check if LLM is configured (API key is set)
  const isLlmConfigured = !statusLoading && systemStatus?.llm_configured;

  const isTailorEnabled =
    Boolean(masterResumeId) && processingStatus === 'ready' && isLlmConfigured;

  const formatDate = (value: string) => {
    if (!value) return t('common.unknown');
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return t('common.unknown');

    const dateLocale =
      locale === 'es' ? 'es-ES' : locale === 'zh' ? 'zh-CN' : locale === 'ja' ? 'ja-JP' : locale === 'tr' ? 'tr-TR' : 'en-US';

    return date.toLocaleDateString(dateLocale, {
      month: 'short',
      day: '2-digit',
      year: 'numeric',
    });
  };

  const checkResumeStatus = useCallback(async (resumeId: string) => {
    try {
      setProcessingStatus('loading');
      const data = await fetchResume(resumeId);
      const status = data.raw_resume?.processing_status || 'pending';
      setProcessingStatus(status as ProcessingStatus);
    } catch (err: unknown) {
      console.error('Failed to check resume status:', err);
      // If resume not found (404), clear the stale localStorage
      if (err instanceof Error && err.message.includes('404')) {
        localStorage.removeItem('master_resume_id');
        setMasterResumeId(null);
        return;
      }
      setProcessingStatus('failed');
    }
  }, []);

  useEffect(() => {
    const storedId = localStorage.getItem('master_resume_id');
    if (storedId) {
      setMasterResumeId(storedId);
      checkResumeStatus(storedId);
    }
  }, [checkResumeStatus]);

  const loadTailoredResumes = useCallback(async () => {
    try {
      const data = await fetchResumeList(true);
      const masterFromList = data.find((r) => r.is_master);
      const storedId = localStorage.getItem('master_resume_id');
      const resolvedMasterId = masterFromList?.resume_id || storedId;

      if (resolvedMasterId) {
        localStorage.setItem('master_resume_id', resolvedMasterId);
        setMasterResumeId(resolvedMasterId);
        checkResumeStatus(resolvedMasterId);
      } else {
        localStorage.removeItem('master_resume_id');
        setMasterResumeId(null);
      }

      const filtered = data.filter((r) => r.resume_id !== resolvedMasterId);
      setTailoredResumes(filtered);

      // Only fetch job descriptions for resumes that are actually tailored
      // (identified by having a non-null parent_id). This avoids N+1 calls
      // for untailored resumes.
      const tailoredWithParent = filtered.filter((r) => r.parent_id);

      // Guard against concurrent invocations overwriting each other
      const requestId = ++loadRequestIdRef.current;

      // Fetch job description snippets for tailored resumes in parallel and attach to state
      // Use a small in-memory cache to avoid re-fetching the same snippet repeatedly.
      const jobSnippets: Record<string, string> = {};
      await Promise.all(
        tailoredWithParent.map(async (r) => {
          // Use cached snippet when available
          if (jobSnippetCacheRef.current[r.resume_id]) {
            jobSnippets[r.resume_id] = jobSnippetCacheRef.current[r.resume_id];
            return;
          }
          try {
            const jd = await fetchJobDescription(r.resume_id);
            const snippet = (jd?.content || '').slice(0, 80);
            jobSnippetCacheRef.current[r.resume_id] = snippet;
            jobSnippets[r.resume_id] = snippet;
          } catch {
            // ignore missing job descriptions and cache empty result
            jobSnippetCacheRef.current[r.resume_id] = '';
            jobSnippets[r.resume_id] = '';
          }
        })
      );

      // Only apply results if this invocation is the latest (prevents stale overwrite)
      if (requestId === loadRequestIdRef.current) {
        setTailoredResumes((prev) =>
          prev.map((r) => ({ ...r, jobSnippet: jobSnippets[r.resume_id] || '' }))
        );
      }
    } catch (err) {
      console.error('Failed to load tailored resumes:', err);
    }
  }, [checkResumeStatus]);

  useEffect(() => {
    loadTailoredResumes();
  }, [loadTailoredResumes]);

  // Refresh list when window gains focus (e.g., returning from viewer after delete)
  useEffect(() => {
    const handleFocus = () => {
      loadTailoredResumes();
    };
    window.addEventListener('focus', handleFocus);
    return () => window.removeEventListener('focus', handleFocus);
  }, [loadTailoredResumes, checkResumeStatus]);

  const handleUploadComplete = (resumeId: string) => {
    localStorage.setItem('master_resume_id', resumeId);
    setMasterResumeId(resumeId);
    // Check status after upload completes
    checkResumeStatus(resumeId);
    // Update cached counters
    incrementResumes();
    setHasMasterResume(true);
  };

  const handleRetryProcessing = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (!masterResumeId) return;
    setIsRetrying(true);
    try {
      const result = await retryProcessing(masterResumeId);
      if (result.processing_status === 'ready') {
        setProcessingStatus('ready');
      } else if (
        result.processing_status === 'processing' ||
        result.processing_status === 'pending'
      ) {
        setProcessingStatus(result.processing_status);
      } else {
        setProcessingStatus('failed');
      }
    } catch (err) {
      console.error('Retry processing failed:', err);
      setProcessingStatus('failed');
    } finally {
      setIsRetrying(false);
    }
  };

  const handleDeleteAndReupload = (e: React.MouseEvent) => {
    e.stopPropagation();
    setShowDeleteDialog(true);
  };

  const confirmDeleteAndReupload = async () => {
    if (!masterResumeId) return;
    try {
      await deleteResume(masterResumeId);
      decrementResumes();
      setHasMasterResume(false);
      localStorage.removeItem('master_resume_id');
      setMasterResumeId(null);
      setProcessingStatus('loading');
      setIsUploadDialogOpen(true);
      await loadTailoredResumes();
    } catch (err) {
      console.error('Failed to delete resume:', err);
    }
  };

  const getStatusDisplay = () => {
    switch (processingStatus) {
      case 'loading':
        return {
          text: t('dashboard.status.checking'),
          icon: <Loader2 className="w-3 h-3 animate-spin" />,
          color: 'text-rose-400',
        };
      case 'processing':
        return {
          text: t('dashboard.status.processing'),
          icon: <Loader2 className="w-3 h-3 animate-spin" />,
          color: 'text-primary',
        };
      case 'ready':
        return { text: t('dashboard.status.ready'), icon: null, color: 'text-emerald-600' };
      case 'failed':
        return {
          text: t('dashboard.status.failed'),
          icon: <AlertCircle className="w-3 h-3" />,
          color: 'text-rose-700',
        };
      default:
        return { text: t('dashboard.status.pending'), icon: null, color: 'text-rose-300' };
    }
  };

  const getMonogram = (title: string): string => {
    const words = title.split(/\s+/).filter((w) => /^[a-zA-Z]/.test(w));
    return words
      .slice(0, 3)
      .map((w) => w.charAt(0).toUpperCase())
      .join('');
  };

  // Premium Rose Palette
  const cardPalette = [
    { bg: '#e0a0a0', fg: '#FFFFFF' }, // Muted Rose
    { bg: '#f4dada', fg: '#4a3a3a' }, // Light Pink
    { bg: '#d4af37', fg: '#FFFFFF' }, // Gold
    { bg: '#ff8787', fg: '#FFFFFF' }, // Soft Red
    { bg: '#a08080', fg: '#FFFFFF' }, // Warm Brown
    { bg: '#fdf8f8', fg: '#4a3a3a' }, // Soft Blush
    { bg: '#ffc9c9', fg: '#4a3a3a' }, // Pastel Pink
    { bg: '#4a3a3a', fg: '#FFFFFF' }, // Dark Warm
  ];

  const hashTitle = (title: string): number => {
    let hash = 0;
    for (let i = 0; i < title.length; i++) {
      hash = (hash << 5) - hash + title.charCodeAt(i);
      hash |= 0;
    }
    return Math.abs(hash);
  };

  const totalCards = 1 + tailoredResumes.length + 1;
  const fillerCount = Math.max(0, (5 - (totalCards % 5)) % 5);
  const extraFillerCount = 5;
  // Use Tailwind classes for fillers now that we have them in config or use specific hex if needed
  // Using the hex values from before to maintain exact look, or we could map them to variants
  const fillerPalette = ['bg-rose-50/50', 'bg-rose-100/30', 'bg-white/50', 'bg-secondary/40'];

  return (
    <div className="space-y-6">
      {/* Configuration Warning Banner */}
      {masterResumeId && !isLlmConfigured && !statusLoading && (
        <div className="border-2 border-warning bg-amber-50 p-4 shadow-sw-default mb-6 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <AlertTriangle className="w-5 h-5 text-warning" />
            <div>
              <p className="font-mono text-sm font-bold uppercase tracking-wider text-amber-800">
                {t('dashboard.llmNotConfiguredTitle')}
              </p>
              <p className="font-mono text-xs text-amber-700 mt-0.5">
                {t('dashboard.llmNotConfiguredMessage')}
              </p>
            </div>
          </div>
          <Link href="/settings">
            <Button variant="outline" size="sm" className="border-warning text-amber-700">
              <Settings className="w-4 h-4 mr-2" />
              {t('nav.settings')}
            </Button>
          </Link>
        </div>
      )}

      <SwissGrid>
        {/* CV to Job Matcher Module */}
        <JobMatcherModule />
        
        {/* 1. Master Resume Logic */}
        {!masterResumeId ? (
          // LLM Not Configured or Upload State
          !isLlmConfigured && !statusLoading ? (
            <Link href="/settings" className="block h-full">
              <Card
                variant="interactive"
                className="aspect-square h-full border-dashed border-warning bg-amber-50"
              >
                <div className="flex-1 flex flex-col justify-between">
                  <div className="w-14 h-14 border-2 border-warning bg-white flex items-center justify-center mb-4">
                    <AlertTriangle className="w-7 h-7 text-warning" />
                  </div>
                  <div>
                    <CardTitle className="text-lg uppercase text-amber-800 mb-2">
                      {t('dashboard.setupRequiredTitle')}
                    </CardTitle>
                    <CardDescription className="text-amber-700 text-xs">
                      {t('dashboard.setupRequiredMessage')}
                    </CardDescription>
                    <div className="flex items-center gap-2 mt-4 text-amber-700 group-hover:text-amber-900">
                      <Settings className="w-4 h-4" />
                      <span className="font-mono text-xs font-bold uppercase">
                        {t('nav.goToSettings')}
                      </span>
                    </div>
                  </div>
                </div>
              </Card>
            </Link>
          ) : (
            <ResumeUploadDialog
              open={isUploadDialogOpen}
              onOpenChange={setIsUploadDialogOpen}
              onUploadComplete={handleUploadComplete}
              trigger={
                <Card
                  variant="interactive"
                  className="aspect-square h-full hover:bg-primary hover:text-white border-dashed border-2 border-rose-200 group rounded-2xl bg-rose-50/30"
                >
                  <div className="flex-1 flex flex-col items-center justify-center p-6 h-full text-center">
                    <CardTitle className="text-2xl font-serif font-bold group-hover:text-white transition-colors leading-[1.2]">
                      {t('dashboard.initializeMasterResume')}
                    </CardTitle>
                  </div>
                </Card>
              }
            />
          )
        ) : (
          // Master Resume Exists
          <Card
            variant="interactive"
            className="aspect-square h-full border-rose-200 shadow-premium-md hover:shadow-premium-xl transition-all duration-300 rounded-2xl"
            onClick={() => router.push(`/resumes/${masterResumeId}`)}
          >
            <div className="flex-1 flex flex-col items-center justify-center h-full p-6 text-center">
              <CardTitle className="text-2xl font-serif font-bold group-hover:text-primary transition-colors leading-[1.2]">
                {t('dashboard.masterResume')}
              </CardTitle>
            </div>
          </Card>
        )}

        {/* 2. Tailored Resumes */}
        {tailoredResumes.map((resume) => {
          const title =
            resume.title || resume.jobSnippet || resume.filename || t('dashboard.tailoredResume');
          return (
            <Card
              key={resume.resume_id}
              variant="interactive"
              className="aspect-square h-full group border-rose-200 shadow-premium-sm hover:shadow-premium-lg transition-all duration-300 rounded-2xl"
              onClick={() => router.push(`/resumes/${resume.resume_id}`)}
            >
              <div className="flex-1 flex flex-col items-center justify-center h-full p-6 text-center">
                <CardTitle className="text-2xl font-serif font-bold group-hover:text-rose-700 transition-colors line-clamp-3 leading-[1.1]">
                  {title}
                </CardTitle>
              </div>
            </Card>
          );
        })}

        {/* 3. Create Tailored Resume */}
        <Link href="/builder" className="block h-full">
          <Card
            variant="interactive"
            className="aspect-square h-full border-dashed border-2 border-rose-200 bg-rose-50/20 rounded-2xl group cursor-pointer"
          >
            <div className="flex-1 flex flex-col items-center justify-center text-center h-full p-6">
              <CardTitle className="text-2xl font-serif font-bold group-hover:text-primary transition-colors leading-[1.2]">
                {t('dashboard.createResume')}
              </CardTitle>
            </div>
          </Card>
        </Link>


        <ConfirmDialog
          open={showDeleteDialog}
          onOpenChange={setShowDeleteDialog}
          title={t('confirmations.deleteMasterResumeTitle')}
          description={t('confirmations.deleteMasterResumeDescription')}
          confirmLabel={t('dashboard.deleteAndReupload')}
          cancelLabel={t('confirmations.keepResumeCancelLabel')}
          onConfirm={confirmDeleteAndReupload}
          variant="danger"
        />
      </SwissGrid>
    </div>
  );
}
