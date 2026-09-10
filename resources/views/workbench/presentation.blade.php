@extends('workbench.layout')
@section('title', ($manifest['name'] ?? 'Presentations').' — CCF6')
@section('subtitle', $manifest['name'] ?? 'Presentations')

@section('content')
@php
    $presentationSummary = $summary['presentations'] ?? [];
    $persistence = $summary['persistence'] ?? [];
    $sequence = $summary['sequence_sensitivity'] ?? [];
    $settling = $summary['settling'] ?? [];
@endphp

<section>
    <div class="panel">
        <p class="lede">{{ $manifest['question'] ?? '' }}</p>
        <p class="muted" style="margin:0">
            Run <code>{{ $run }}</code> · {{ $presentationSummary['total'] ?? 0 }} independent Presentations ·
            {{ $presentationSummary['samples'] ?? 0 }} Samples
        </p>
    </div>
</section>

<section>
    <h2>Protocol checks</h2>
    <div class="panel">
        <table>
            <thead><tr><th class="l">Check</th><th>Recorded result</th></tr></thead>
            <tbody>
            <tr><td class="l">Reset only at Presentation boundaries</td><td>{{ ($presentationSummary['reset_at_boundaries'] ?? false) ? 'pass' : 'fail' }}</td></tr>
            <tr><td class="l">State continuity between Samples</td><td>{{ ($presentationSummary['state_continuity_between_samples'] ?? false) ? 'pass' : 'fail' }}</td></tr>
            <tr><td class="l">Minimum visual retention</td><td>{{ number_format($persistence['minimum_visual_retention_ratio'] ?? 0, 6) }}</td></tr>
            <tr><td class="l">Sequence-sensitive</td><td>{{ ($sequence['passed'] ?? false) ? 'Sequence-sensitive: pass' : 'Sequence-sensitive: fail' }}</td></tr>
            <tr><td class="l">Same-bag sequence comparisons</td><td>{{ $sequence['same_bag_sequence_pairs'] ?? 0 }}</td></tr>
            <tr><td class="l">Distinct trajectory comparisons</td><td>{{ $sequence['distinct_trajectory_pairs'] ?? 0 }}</td></tr>
            <tr><td class="l">Minimum trajectory distance</td><td>{{ $sequence['minimum_trajectory_distance'] ?? 0 }}</td></tr>
            <tr><td class="l">Settling failures</td><td>{{ $settling['failures'] ?? 0 }}</td></tr>
            <tr><td class="l">Sample duration range</td><td>{{ $settling['duration_ticks_min'] ?? 0 }}–{{ $settling['duration_ticks_max'] ?? 0 }} ticks</td></tr>
            </tbody>
        </table>
    </div>
</section>

<section>
    <h2>Minimum Functional Web topology</h2>
    <div class="panel">
        <p class="lede">Every declared Population uses the same ordinary Column mechanics.</p>
        <table>
            <thead><tr><th class="l">Population</th><th>Columns</th><th class="l">Provenance</th><th class="l">Wiring role</th></tr></thead>
            <tbody>
            @foreach (($topology['populations'] ?? []) as $population)
                <tr>
                    <td class="l"><code>{{ $population['id'] }}</code></td>
                    <td>{{ $population['columns'] }}</td>
                    <td class="l">{{ $population['provenance'] }}</td>
                    <td class="l">{{ $population['wiring_role'] }}</td>
                </tr>
            @endforeach
            </tbody>
        </table>
    </div>
</section>

<section>
    <h2>Presentation trajectories</h2>
    @foreach ($presentations as $presentation)
        <div class="panel" style="margin-bottom:16px">
            <h3><code>{{ $presentation['id'] }}</code> · {{ $presentation['condition'] }}</h3>
            <p class="muted">
                <code>{{ $presentation['category_id'] }}</code> with <code>{{ $presentation['pseudoword_id'] }}</code> ·
                order {{ implode(' → ', $presentation['segments']) }} ·
                Success Signal {{ number_format($presentation['success_signal'], 1) }} ·
                {{ $presentation['settling_failures'] }} settling failures
            </p>
            <table>
                <thead><tr><th>Sample</th><th class="l">Kind</th><th class="l">Identity</th><th class="l">Active physical features</th><th>Duration</th><th>Settled</th><th>Final delta</th></tr></thead>
                <tbody>
                @foreach ($presentation['samples'] as $sample)
                    <tr>
                        <td>{{ $sample['number'] }}</td>
                        <td class="l">{{ $sample['kind'] }}</td>
                        <td class="l"><code>{{ $sample['id'] }}</code></td>
                        <td class="l">{{ implode(', ', $sample['active_features']) }}</td>
                        <td>{{ $sample['duration_ticks'] }} ticks</td>
                        <td>{{ $sample['settled'] ? 'yes' : 'no' }}</td>
                        <td>{{ $sample['final_delta'] }}</td>
                    </tr>
                    <tr>
                        <td></td>
                        <td colspan="6" class="l">
                            <details>
                                <summary>Settled state and tick-by-tick Output trajectory</summary>
                                <p><code>{{ json_encode($sample['settled_activity']) }}</code></p>
                                <pre style="overflow:auto;max-height:240px"><code>{{ json_encode($sample['output_trajectory']) }}</code></pre>
                            </details>
                        </td>
                    </tr>
                @endforeach
                </tbody>
            </table>
        </div>
    @endforeach
</section>
@endsection
