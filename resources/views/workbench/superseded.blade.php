@extends('workbench.layout')
@section('title', ($manifest['name'] ?? 'Run').' — CCF6')
@section('subtitle', $manifest['name'] ?? 'Run')

@section('content')
<section>
    <div class="panel">
        <p class="verdict">This run predates the current architecture.</p>
        <p class="muted" style="max-width:70ch">
            Its artifact contract does not match the current NCL-only Column network.
            The numbers are not comparable with a current run, so the workbench preserves
            the artifact without interpreting it through the new architecture.
        </p>
        <table>
            <thead><tr><th class="l">Field</th><th class="l">Value</th></tr></thead>
            <tbody>
            <tr><td class="l">Run</td><td class="l"><code>{{ $run }}</code></td></tr>
            <tr><td class="l">Kind</td><td class="l"><code>{{ $manifest['kind'] ?? '—' }}</code></td></tr>
            <tr><td class="l">Started</td><td class="l muted">{{ $manifest['started'] ?? '—' }}</td></tr>
            <tr><td class="l">Digest</td><td class="l"><code>{{ $manifest['digest'] ?? '—' }}</code></td></tr>
            </tbody>
        </table>
        <p class="muted" style="margin:16px 0 0">
            The summary it recorded is still on disk in the artifact directory.
        </p>
    </div>
</section>

<style>
    .verdict { font-size: 16px; font-weight: 600; margin: 0 0 14px; padding: 12px 16px;
               border-radius: 8px; border: 1px solid var(--line); background: #fff; }
</style>
@endsection
