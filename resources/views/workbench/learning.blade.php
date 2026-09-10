@extends('workbench.layout')
@section('title', ($manifest['name'] ?? 'Learning').' — CCF6')
@section('subtitle', $manifest['name'] ?? 'Learning')

@section('content')
@php
    $acquisition = $summary['acquisition'] ?? [];
    $effects = $summary['learning'] ?? [];
    $eligibility = $summary['eligibility'] ?? [];
    $settling = $summary['settling'] ?? [];
@endphp

<section>
    <div class="panel">
        <p class="lede">{{ $manifest['question'] ?? '' }}</p>
        <p class="muted" style="margin:0">
            Run <code>{{ $run }}</code> · {{ $acquisition['epochs'] ?? 0 }} epochs ·
            {{ $acquisition['presentations'] ?? 0 }} acquisition Presentations
        </p>
    </div>
</section>

<section>
    <h2>Success-gated learning</h2>
    <div class="panel">
        <table>
            <thead><tr><th class="l">Recorded check</th><th>Result</th></tr></thead>
            <tbody>
            <tr><td class="l">Balanced acquisition</td><td>{{ ($acquisition['balanced'] ?? false) ? 'Balanced acquisition: yes' : 'Balanced acquisition: no' }}</td></tr>
            <tr><td class="l">Correct / mismatched</td><td>{{ $acquisition['correct'] ?? 0 }} / {{ $acquisition['mismatched'] ?? 0 }}</td></tr>
            <tr><td class="l">Successful Presentations changing weights</td><td>{{ $effects['successful_presentations_changed'] ?? 0 }}</td></tr>
            <tr><td class="l">Unsuccessful Presentations changing weights</td><td>{{ $effects['unsuccessful_presentations_changed'] ?? 0 }}</td></tr>
            <tr><td class="l">Ascending durable shift</td><td>{{ $effects['ascending_weight_shift_l2'] ?? 0 }}</td></tr>
            <tr><td class="l">Descending durable shift</td><td>{{ $effects['descending_weight_shift_l2'] ?? 0 }}</td></tr>
            <tr><td class="l">Maximum incoming-normalization error</td><td>{{ $effects['maximum_normalization_error'] ?? 0 }}</td></tr>
            <tr><td class="l">Weights within bounds</td><td>{{ ($effects['weights_within_bounds'] ?? false) ? 'yes' : 'no' }}</td></tr>
            <tr><td class="l">Eligibility range</td><td>{{ $eligibility['minimum'] ?? 0 }}–{{ $eligibility['maximum'] ?? 0 }}</td></tr>
            <tr><td class="l">Eligibility reset at Presentation boundaries</td><td>{{ ($eligibility['reset_at_presentation_boundaries'] ?? false) ? 'yes' : 'no' }}</td></tr>
            <tr><td class="l">Eligibility continuous between Samples</td><td>{{ ($eligibility['continuous_between_samples'] ?? false) ? 'yes' : 'no' }}</td></tr>
            <tr><td class="l">Settling failures</td><td>{{ $settling['failures'] ?? 0 }}</td></tr>
            </tbody>
        </table>
    </div>
</section>

<section>
    <h2>Successful versus unsuccessful effects</h2>
    @foreach (($learning['presentations'] ?? []) as $presentation)
        <div class="panel" style="margin-bottom:16px">
            <h3><code>{{ $presentation['presentation_id'] }}</code> · {{ $presentation['condition'] }}</h3>
            <p class="muted">
                Epoch {{ $presentation['epoch'] }} ·
                <code>{{ $presentation['category_id'] }}</code> with <code>{{ $presentation['pseudoword_id'] }}</code> ·
                Success Signal {{ number_format($presentation['success_signal'], 1) }} ·
                {{ $presentation['durable_weights_changed'] ? 'Durable weights changed' : 'No durable change' }}
            </p>
            <table>
                <thead>
                    <tr><th class="l">Projection</th><th>Ascending Eligibility</th><th>Descending Eligibility</th><th>Ascending changed</th><th>Descending changed</th></tr>
                </thead>
                <tbody>
                @foreach ($presentation['projections'] as $projection)
                    <tr>
                        <td class="l"><code>{{ $projection['id'] }}</code></td>
                        <td>{{ $projection['eligibility']['ascending_sum'] }}</td>
                        <td>{{ $projection['eligibility']['descending_sum'] }}</td>
                        <td>{{ $projection['ascending']['changed_connections'] }}</td>
                        <td>{{ $projection['descending']['changed_connections'] }}</td>
                    </tr>
                    <tr>
                        <td></td>
                        <td colspan="4" class="l">
                            <details>
                                <summary>Pre/post directional weights</summary>
                                <p>Ascending pre <code>{{ json_encode($projection['ascending']['pre_weights']) }}</code></p>
                                <p>Ascending post <code>{{ json_encode($projection['ascending']['post_weights']) }}</code></p>
                                <p>Descending pre <code>{{ json_encode($projection['descending']['pre_weights']) }}</code></p>
                                <p>Descending post <code>{{ json_encode($projection['descending']['post_weights']) }}</code></p>
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
