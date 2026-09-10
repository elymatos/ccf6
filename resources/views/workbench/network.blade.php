@extends('workbench.layout')
@section('title', ($manifest['name'] ?? 'Network').' — CCF6')
@section('subtitle', $manifest['name'] ?? 'Network')

@section('content')
@php
    $network = $summary['network'] ?? [];
    $settling = $summary['settling'] ?? [];
    $stimulus = $summary['stimulus'] ?? [];
    $activitySummary = $summary['activity'] ?? [];
@endphp

<section>
    <div class="panel">
        <p class="lede">{{ $manifest['question'] ?? '' }}</p>
        <p class="muted" style="margin:0">
            Run <code>{{ $run }}</code> · contract <code>{{ $manifest['contract'] ?? '—' }}</code> ·
            seed <code>{{ $topology['seed'] ?? '—' }}</code>
        </p>
    </div>
</section>

<section>
    <h2>Settling</h2>
    <div class="panel">
        <p class="lede">
            <strong>{{ ($settling['success'] ?? false) ? 'Settled successfully' : 'Settling failed at max ticks' }}</strong>.
            Stability requires the declared epsilon for consecutive stable ticks.
        </p>
        <table>
            <thead><tr><th class="l">Measure</th><th>Recorded value</th></tr></thead>
            <tbody>
            <tr><td class="l">Ticks</td><td>{{ $settling['ticks'] ?? 0 }}</td></tr>
            <tr><td class="l">Consecutive stable ticks</td><td>{{ $settling['stable_ticks'] ?? 0 }}</td></tr>
            <tr><td class="l">Required epsilon</td><td>{{ $settling['epsilon'] ?? '—' }}</td></tr>
            <tr><td class="l">Final Output delta</td><td>{{ $settling['final_delta'] ?? '—' }}</td></tr>
            <tr><td class="l">Maximum ticks</td><td>{{ $settling['max_ticks'] ?? 0 }}</td></tr>
            <tr><td class="l">Max-tick failure</td><td>{{ ($settling['max_ticks_reached'] ?? false) ? 'yes' : 'no' }}</td></tr>
            </tbody>
        </table>
    </div>
</section>

<section>
    <h2>Generated stimulus and activity</h2>
    <div class="panel">
        <p class="lede">
            <code>{{ $stimulus['category_id'] ?? '—' }}</code> supplied
            {{ $stimulus['active_features'] ?? 0 }} physical properties to
            <code>{{ $stimulus['population_id'] ?? '—' }}</code>.
            Every Column uses the same Input, Integration, and Output mechanics.
        </p>
        <table>
            <thead><tr><th class="l">Compartment</th><th>Maximum settled activity</th></tr></thead>
            <tbody>
            <tr><td class="l">Input</td><td>{{ number_format($activitySummary['input_max'] ?? 0, 6) }}</td></tr>
            <tr><td class="l">Integration</td><td>{{ number_format($activitySummary['integration_max'] ?? 0, 6) }}</td></tr>
            <tr><td class="l">Output</td><td>{{ number_format($activitySummary['output_max'] ?? 0, 6) }}</td></tr>
            </tbody>
        </table>
        <table style="margin-top:20px">
            <thead><tr><th class="l">Column</th><th>Initial Input</th><th>Initial Integration</th><th>Initial Output</th><th>Settled Input</th><th>Settled Integration</th><th>Settled Output</th></tr></thead>
            <tbody>
            @foreach (($activity['labels'] ?? []) as $index => $label)
                <tr>
                    <td class="l"><code>{{ $label }}</code></td>
                    @foreach (($activity['initial'][$index] ?? [0, 0, 0]) as $value)
                        <td>{{ number_format($value, 6) }}</td>
                    @endforeach
                    @foreach (($activity['settled'][$index] ?? [0, 0, 0]) as $value)
                        <td>{{ number_format($value, 6) }}</td>
                    @endforeach
                </tr>
            @endforeach
            </tbody>
        </table>
    </div>
</section>

<section>
    <h2>Populations and local inhibition</h2>
    @foreach (($topology['populations'] ?? []) as $population)
        <div class="panel" style="margin-bottom:16px">
            <h3><code>{{ $population['id'] }}</code></h3>
            <p class="muted">
                {{ $population['columns'] }} ordinary Columns · {{ $population['provenance'] }} ·
                {{ $population['wiring_role'] }} · inhibition radius {{ $population['inhibition']['radius'] }},
                strength {{ $population['inhibition']['strength'] }},
                {{ $population['inhibition']['connections'] }} generated connections
            </p>
            <table>
                <thead><tr><th class="l">Column</th><th>Threshold</th></tr></thead>
                <tbody>
                @foreach ($population['thresholds'] as $column => $threshold)
                    <tr><td class="l"><code>{{ $population['id'] }}#{{ $column }}</code></td><td>{{ number_format($threshold, 6) }}</td></tr>
                @endforeach
                </tbody>
            </table>
            <table style="margin-top:20px">
                <thead><tr><th>Inhibitory source</th><th>Inhibitory target</th><th>Weight</th></tr></thead>
                <tbody>
                @foreach ($population['inhibition']['endpoints'] as $endpoint)
                    <tr>
                        <td>{{ $endpoint['source_column'] }}</td>
                        <td>{{ $endpoint['target_column'] }}</td>
                        <td>{{ number_format($endpoint['weight'], 6) }}</td>
                    </tr>
                @endforeach
                </tbody>
            </table>
        </div>
    @endforeach
</section>

<section>
    <h2>Reciprocal projection connectivity</h2>
    @foreach (($topology['projections'] ?? []) as $projection)
        <div class="panel" style="margin-bottom:16px">
            <h3><code>{{ $projection['id'] }}</code></h3>
            <p class="muted">
                {{ $projection['source'] }} ↔ {{ $projection['target'] }} ·
                {{ $projection['connections'] }} shared endpoints · fan-in {{ $projection['fan_in'] }} ·
                incoming norm {{ $projection['incoming_norm'] }} · independently initialized directions
            </p>
            <table>
                <thead><tr><th>Source Column</th><th>Target Column</th><th>Ascending weight</th><th>Descending weight</th><th>Ascending Eligibility</th><th>Descending Eligibility</th></tr></thead>
                <tbody>
                @foreach ($projection['endpoints'] as $endpoint)
                    <tr>
                        <td>{{ $endpoint['source_column'] }}</td>
                        <td>{{ $endpoint['target_column'] }}</td>
                        <td>{{ number_format($endpoint['ascending_weight'], 6) }}</td>
                        <td>{{ number_format($endpoint['descending_weight'], 6) }}</td>
                        <td>{{ number_format($endpoint['ascending_eligibility'], 6) }}</td>
                        <td>{{ number_format($endpoint['descending_eligibility'], 6) }}</td>
                    </tr>
                @endforeach
                </tbody>
            </table>
        </div>
    @endforeach
</section>
@endsection
