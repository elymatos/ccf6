@extends('workbench.layout')
@section('title', ($manifest['name'] ?? 'Run').' — CCF6')
@section('subtitle', $manifest['name'] ?? 'Run')

@section('content')
@php
    $css = ['white'=>'#fff','red'=>'#d94040','green'=>'#3f9e4d','blue'=>'#3a6fd8',
            'yellow'=>'#e3c020','cyan'=>'#31b7c2','magenta'=>'#bf47b5','black'=>'#222'];
    $overall = $summary['overall'] ?? [];
    $recruitment = $summary['recruitment'] ?? [];
    $completion = $summary['completion'] ?? [];
    $presentation = $summary['presentation'] ?? [];
@endphp

<section>
    <div class="panel">
        <p class="lede">{{ $manifest['question'] ?? '' }}</p>
        <p class="muted" style="margin:0">
            Run <code>{{ $run }}</code> · kind <code>{{ $manifest['kind'] ?? '—' }}</code> ·
            {{ number_format($manifest['seconds'] ?? 0, 1) }}s ·
            contract <code>{{ $manifest['contract'] ?? '—' }}</code>
        </p>
    </div>
</section>

<section>
    <h2>Network result</h2>
    <div class="panel">
        <table>
            <thead><tr><th class="l">Measure</th><th>Value</th></tr></thead>
            <tbody>
            <tr><td class="l">Columns</td><td>{{ number_format($overall['columns'] ?? 0) }}</td></tr>
            <tr><td class="l">Best figure separation</td><td>{{ number_format($overall['figure_separation_max'] ?? 0, 4) }}</td></tr>
            <tr><td class="l">Population separation</td><td>{{ number_format($overall['population_separation'] ?? 0, 4) }}</td></tr>
            <tr><td class="l">Best shape selectivity</td><td>{{ number_format($overall['shape_selectivity_max'] ?? 0, 4) }}</td></tr>
            <tr><td class="l">Best colour selectivity</td><td>{{ number_format($overall['colour_selectivity_max'] ?? 0, 4) }}</td></tr>
            <tr><td class="l">Best conjunction selectivity</td><td>{{ number_format($overall['conjunction_selectivity_max'] ?? 0, 4) }}</td></tr>
            </tbody>
        </table>
    </div>
</section>

<section>
    <h2>Recruitment and cardinal candidates</h2>
    <div class="panel">
        <p class="lede">
            {{ $recruitment['epochs'] ?? 0 }} training epochs. A candidate is a committed
            convergence Column, not a declared concept or a proven biological cardinal.
        </p>
        <table>
            <thead><tr><th class="l">Association Population</th><th>Candidates</th></tr></thead>
            <tbody>
            @forelse (($recruitment['cardinal_candidates'] ?? []) as $population => $count)
                <tr><td class="l"><code>{{ $population }}</code></td><td>{{ $count }}</td></tr>
            @empty
                <tr><td class="l muted">No association Populations</td><td>0</td></tr>
            @endforelse
            </tbody>
        </table>
    </div>
</section>

<section>
    <h2>Partial cues and reciprocal reactivation</h2>
    <div class="panel">
        <table>
            <thead><tr><th class="l">Measure</th><th>Cosine similarity</th></tr></thead>
            <tbody>
            @foreach ($completion as $name => $value)
                <tr><td class="l">{{ str_replace('_', ' ', $name) }}</td><td>{{ number_format($value, 4) }}</td></tr>
            @endforeach
            </tbody>
        </table>
        <p class="muted" style="max-width:72ch;margin-bottom:0">
            These values compare partial-cue activity with the corresponding full presentation.
            They measure current behavior; they do not imply successful completion without a
            trained-versus-untrained comparison.
        </p>
    </div>
</section>

<section>
    <h2>Populations and connections</h2>
    <div class="panel">
        @foreach ($populations as $name => $population)
            <h3><code>{{ $name }}</code> <span class="muted">— {{ $population['role'] }}, {{ $population['modality'] ?? 'no direct modality' }}</span></h3>
            @if ($population['sources'])
                <p class="muted">Receives from {{ implode(', ', $population['sources']) }}</p>
            @endif
            <table>
                <thead><tr><th class="l">Level</th><th>Columns</th><th class="l">Source</th><th>Fan-in</th><th>Connections</th><th class="l">Competition</th></tr></thead>
                <tbody>
                @foreach ($population['levels'] as $level)
                    <tr>
                        <td class="l"><code>{{ $level['level'] }}</code></td>
                        <td>{{ $level['columns'] }}</td>
                        <td class="l muted">{{ $level['source'] }}</td>
                        <td>{{ $level['fan_in'] }}</td>
                        <td>{{ number_format($level['connections']) }}</td>
                        <td class="l muted">{{ $level['competition'] }}</td>
                    </tr>
                @endforeach
                </tbody>
            </table>
        @endforeach
    </div>
</section>

<section>
    <h2>Presentations</h2>
    <div class="panel">
        <p class="lede">
            {{ $presentation['samples_per_figure'] ?? 0 }} samples per figure,
            {{ $presentation['origins'] ?? 0 }} origins, order
            <code>{{ $presentation['visiting_order'] ?? '—' }}</code>.
        </p>
        <div class="row">
        @foreach ($snapshots as $snapshot)
            <figure>
                <div class="world" style="grid-template-columns:repeat({{ count($snapshot['world'][0]) }},18px)">
                    @foreach ($snapshot['world'] as $i => $row)
                        @foreach ($row as $j => $colour)
                            <i style="background:{{ $css[$palette[$colour] ?? 'white'] ?? '#fff' }}"
                               class="{{ in_array([$i,$j], $snapshot['presentation']['positions'] ?? []) ? 'mark' : '' }}"></i>
                        @endforeach
                    @endforeach
                </div>
                <figcaption><strong>{{ $snapshot['figure'] }}</strong> at ({{ implode(',', $snapshot['origin']) }})</figcaption>
            </figure>
        @endforeach
        </div>
    </div>
</section>

<style>
    .world { display:grid;gap:1px;background:var(--line);padding:1px; }
    .world i { display:block;width:18px;height:18px; }
    .world i.mark { outline:2px solid #111;outline-offset:-2px;z-index:1; }
</style>
@endsection
