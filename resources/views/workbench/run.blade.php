@extends('workbench.layout')
@section('title', ($manifest['name'] ?? 'Run').' — CCF6')
@section('subtitle', $manifest['name'] ?? 'Run')

@section('content')
@php
    $css = ['white'=>'#fff','red'=>'#d94040','green'=>'#3f9e4d','blue'=>'#3a6fd8',
            'yellow'=>'#e3c020','cyan'=>'#31b7c2','magenta'=>'#bf47b5','black'=>'#222'];
    $overall = $summary['overall'] ?? [];
    $presentation = $summary['presentation'] ?? [];
    $nothing = ($overall['shape_selectivity_max'] ?? 0) < 0.01;
@endphp

<section>
    <div class="panel">
        <p class="lede">{{ $manifest['question'] ?? '' }}</p>
        <p class="muted" style="margin:0">
            Run <code>{{ $run }}</code> · kind <code>{{ $manifest['kind'] ?? '—' }}</code> ·
            {{ number_format($manifest['seconds'] ?? 0, 1) }}s ·
            structures {{ implode(', ', $structures) }}
        </p>
    </div>
</section>

<section>
    <h2>What this run represented</h2>
    <div class="panel">
        @if ($nothing)
            <p class="verdict">
                Nothing was learned, and nothing was expected to be. This is a baseline:
                the numbers below come from connectivity fixed at construction, and they
                are what a local learning rule has to beat.
            </p>
        @endif
        <table>
            <thead><tr><th class="l">Measure</th><th>Value</th></tr></thead>
            <tbody>
            <tr><td class="l">Columns</td><td>{{ $overall['columns'] ?? 0 }}</td></tr>
            <tr><td class="l">Active / silent</td>
                <td>{{ $overall['active_columns'] ?? 0 }} / {{ $overall['silent_columns'] ?? 0 }}</td></tr>
            <tr><td class="l">Best shape selectivity</td>
                <td><strong>{{ number_format($overall['shape_selectivity_max'] ?? 0, 4) }}</strong></td></tr>
            <tr><td class="l">Best position selectivity</td>
                <td>{{ number_format($overall['position_selectivity_max'] ?? 0, 4) }}</td></tr>
            </tbody>
        </table>
        <p class="muted" style="max-width:70ch;margin:14px 0 0">
            <strong>Shape</strong> and <strong>position</strong> were crossed factorially, so
            each Column's variance can be attributed to the factor it actually follows.
            A Column that never moved scores zero on both rather than being credited with
            perfect selectivity for nothing.
        </p>
    </div>
</section>

<section>
    <h2>What was shown</h2>
    <div class="panel">
        <p class="lede">
            A figure is presented as a <strong>sequence</strong>: Ego visits each part in the
            declared order, and the offset between successive stops is the given Relation.
            {{ $presentation['stops_per_figure'] ?? 0 }} stops per figure,
            {{ $presentation['relations_per_figure'] ?? 0 }} Relations,
            {{ $presentation['origins'] ?? 0 }} World positions,
            order <code>{{ $presentation['visiting_order'] ?? '—' }}</code>.
        </p>
        @foreach ($snapshots as $index => $snapshot)
            <div class="row" style="margin-bottom:22px;align-items:flex-start">
                <figure>
                    <div class="world" style="grid-template-columns:repeat({{ count($snapshot['world'][0]) }},18px)">
                        @foreach ($snapshot['world'] as $i => $row)
                            @foreach ($row as $j => $colour)
                                <i style="background:{{ $css[$palette[$colour] ?? 'white'] ?? '#fff' }}"
                                   class="{{ in_array([$i,$j], $snapshot['presentation']['positions'] ?? []) ? 'mark' : '' }}"></i>
                            @endforeach
                        @endforeach
                    </div>
                    <figcaption>
                        <strong>{{ $snapshot['figure'] }}</strong><br>
                        at ({{ implode(',', $snapshot['origin']) }})
                    </figcaption>
                </figure>
                <figure style="max-width:40ch">
                    <figcaption style="text-align:left">
                        <strong>Relations walked</strong><br>
                        @foreach ($snapshot['presentation']['relations'] ?? [] as $relation)
                            <code>({{ implode(',', $relation) }})</code>{{ !$loop->last ? ' → ' : '' }}
                        @endforeach
                    </figcaption>
                </figure>
                @if (!empty($snapshot['schema']))
                    @foreach ($snapshot['schema'] as $module => $grid)
                        <figure>
                            <canvas class="heat" data-snapshot="{{ $index }}" data-module="{{ $module }}"
                                    width="{{ count($grid[0]) }}" height="{{ count($grid) }}"
                                    style="width:{{ count($grid[0]) * 18 }}px;height:{{ count($grid) * 18 }}px"></canvas>
                            <figcaption>Schema module {{ $module }}</figcaption>
                        </figure>
                    @endforeach
                @endif
            </div>
        @endforeach
    </div>
</section>

<section>
    <h2>The Web — what things are</h2>
    <div class="panel">
        <p class="lede">
            <strong>Fan-in</strong> is how many Columns send into one Column, and it is a
            declared quantity: a Column drawing from everything below it would be identical
            to every other such Column and would distinguish nothing. Every number here was
            written by the code that built the connections.
        </p>
        @foreach ($spaces as $name => $detail)
            <h3 style="font-size:14px;margin:20px 0 8px">
                <code>{{ $name }}</code>
                <span class="muted" style="font-weight:400">
                    — {{ $detail['cortical_area'] }} cortex,
                    {{ $detail['modality'] ?? 'no modality of its own' }}
                </span>
            </h3>
            <table>
                <thead>
                <tr><th class="l">Level</th><th>Columns</th><th class="l">Receives from</th>
                    <th class="l">How</th><th>Fan-in</th><th>Connections</th>
                    <th>Competes with</th><th class="l">Feedback from</th>
                    <th>Shape sel.</th><th>Position sel.</th></tr>
                </thead>
                <tbody>
                @foreach ($detail['levels'] as $row)
                    @php $level = $summary['by_level'][$row['level']] ?? []; @endphp
                    <tr>
                        <td class="l"><code>{{ $row['level'] }}</code></td>
                        <td>{{ $row['columns'] }}</td>
                        <td class="l muted">{{ $row['source'] }}</td>
                        <td class="l muted">{{ $row['rule'] }}</td>
                        <td>{{ $row['fan_in'] }}</td>
                        <td class="muted">{{ number_format($row['connections']) }}</td>
                        <td>{{ $row['competitors'] }}</td>
                        <td class="l muted">{{ $row['feedback_from'] ?? '—' }}</td>
                        <td>{{ number_format($level['shape_selectivity_max'] ?? 0, 3) }}</td>
                        <td>{{ number_format($level['position_selectivity_max'] ?? 0, 3) }}</td>
                    </tr>
                @endforeach
                </tbody>
            </table>
        @endforeach
        @if ($convergenceSources)
            <p class="muted" style="margin:18px 0 0;max-width:70ch">
                A <strong>Cardinal Node</strong> can only form where several Spaces meet, so the
                convergence Space is the only place one could appear. It receives
                @foreach ($convergenceSources as $source)
                    <code>{{ $source['level'] }}</code> ({{ $source['columns'] }} Columns){{ !$loop->last ? ' and ' : '' }}
                @endforeach.
            </p>
        @endif
    </div>
</section>

@if ($schema)
<section>
    <h2>The Schema — how things change</h2>
    <div class="panel">
        <p class="lede">
            Periodic modules over a torus. A Relation moves every module's bump by the same
            offset, so positions separate, two routes to one place agree, and a route never
            walked arrives where the structure implies. The Schema never sees what occupies
            a position.
        </p>
        <table>
            <thead><tr><th class="l">Property</th><th>Value</th><th class="l">Why it matters</th></tr></thead>
            <tbody>
            <tr><td class="l">Columns</td><td>{{ $schema['columns'] }}</td>
                <td class="l muted">Modules {{ implode(', ', $schema['periods']) }}</td></tr>
            <tr><td class="l">Capacity</td><td>{{ $schema['capacity'] }}</td>
                <td class="l muted">How far the code runs before it repeats</td></tr>
            <tr><td class="l">Distinct states</td>
                <td>{{ $summary['schema']['distinct_states'] ?? 0 }} / {{ $summary['schema']['positions_visited'] ?? 0 }}</td>
                <td class="l muted">Two positions sharing a state could not hold different memories</td></tr>
            <tr><td class="l">Path-consistency error</td>
                <td>{{ number_format($summary['schema']['path_consistency_error'] ?? 0, 9) }}</td>
                <td class="l muted">Reaching one place two ways must give one state</td></tr>
            </tbody>
        </table>
    </div>
</section>
@endif

@if ($index)
<section>
    <h2>The Index — what happened where</h2>
    <div class="panel">
        <p class="lede">
            Binds the Web's convergence output to the Schema's state, in one exposure. Its
            pressure is the opposite of the Web's: entries must stay apart rather than
            converge, which is why it is a separate structure.
        </p>
        <table>
            <thead><tr><th class="l">Measure</th><th>Value</th></tr></thead>
            <tbody>
            <tr><td class="l">Bindings from the last presentation</td>
                <td>{{ $summary['index']['entries'] ?? 0 }}</td></tr>
            <tr><td class="l">Bindings that had content to bind</td>
                <td>{{ $summary['index']['bindings_with_content'] ?? 0 }}</td></tr>
            <tr><td class="l">Stops across the whole run</td>
                <td>{{ number_format($summary['index']['total_stops_in_run'] ?? 0) }}</td></tr>
            <tr><td class="l">Completion from a positional cue</td>
                <td><strong>{{ number_format(100 * ($summary['index']['completion_accuracy'] ?? 0), 1) }}%</strong></td></tr>
            </tbody>
        </table>
    </div>
</section>
@endif

<style>
    .verdict { font-size: 16px; font-weight: 600; margin: 0 0 18px; padding: 12px 16px;
               border-radius: 8px; border: 1px solid var(--line); background: #fff; }
    .world { display: grid; gap: 1px; background: var(--line); padding: 1px; }
    .world i { display: block; width: 18px; height: 18px; }
    .world i.mark { outline: 2px solid #111; outline-offset: -2px; z-index: 1; }
</style>

<script>
    const SNAPSHOTS = @json($snapshots);
    document.querySelectorAll('canvas.heat').forEach(canvas => {
        const snapshot = SNAPSHOTS[Number(canvas.dataset.snapshot)];
        const grid = snapshot.schema[Number(canvas.dataset.module)];
        const context = canvas.getContext('2d');
        const image = context.createImageData(canvas.width, canvas.height);
        grid.forEach((row, i) => row.forEach((value, j) => {
            const at = (i * canvas.width + j) * 4;
            const level = Math.max(0, Math.min(1, value));
            image.data[at] = 20 + 200 * level;
            image.data[at + 1] = 30 + 120 * level;
            image.data[at + 2] = 60 + 40 * level;
            image.data[at + 3] = 255;
        }));
        context.putImageData(image, 0, 0);
        canvas.style.imageRendering = 'pixelated';
    });
</script>
@endsection
