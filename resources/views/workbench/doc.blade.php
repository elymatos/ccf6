@extends('workbench.layout')
@section('title', $title.' — CCF6')
@section('subtitle', 'Documentation')

@section('content')
<article class="panel prose">{!! $body !!}</article>
<style>
    .prose { max-width: 76ch; }
    .prose h1 { font-size: 26px; margin: 0 0 20px; letter-spacing: -.01em; }
    .prose h2 { font-size: 19px; text-transform: none; letter-spacing: 0;
                color: var(--ink); margin: 34px 0 10px; }
    .prose h3 { font-size: 16px; margin: 24px 0 8px; }
    .prose p, .prose li { max-width: 72ch; }
    .prose table { margin: 16px 0; }
    .prose code { background: #fff; border: 1px solid var(--line);
                  border-radius: 3px; padding: 1px 5px; }
    .prose ol, .prose ul { padding-left: 22px; }
    .prose li { margin-bottom: 6px; }
    .prose strong { font-weight: 650; }
</style>
@endsection
