@extends('workbench.layout')
@section('title', ($manifest['name'] ?? 'Unsupported artifact').' — CCF6')
@section('subtitle', $manifest['name'] ?? 'Unsupported artifact')

@section('content')
<section>
    <div class="panel">
        <p class="verdict">Unsupported or malformed artifact</p>
        <p class="muted" style="max-width:70ch">{{ $problem }}</p>
        <p class="muted" style="max-width:70ch">
            The workbench will not infer missing values, reinterpret an obsolete contract,
            or recompute results. Files remain unchanged on disk for external inspection.
        </p>
        <table>
            <thead><tr><th class="l">Field</th><th class="l">Value</th></tr></thead>
            <tbody>
            <tr><td class="l">Run</td><td class="l"><code>{{ $run }}</code></td></tr>
            <tr><td class="l">Contract</td><td class="l"><code>{{ $manifest['contract'] ?? '—' }}</code></td></tr>
            <tr><td class="l">Kind</td><td class="l"><code>{{ $manifest['kind'] ?? '—' }}</code></td></tr>
            <tr><td class="l">Started</td><td class="l muted">{{ $manifest['started'] ?? '—' }}</td></tr>
            <tr><td class="l">Digest</td><td class="l"><code>{{ $manifest['digest'] ?? '—' }}</code></td></tr>
            </tbody>
        </table>
    </div>
</section>

<style>
    .verdict { font-size: 16px; font-weight: 600; margin: 0 0 14px; padding: 12px 16px;
               border-radius: 8px; border: 1px solid var(--line); background: #fff; }
</style>
@endsection
