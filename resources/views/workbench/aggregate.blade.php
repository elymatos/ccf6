@extends('workbench.layout')
@section('title', ($manifest['name'] ?? 'Replicated milestone').' — CCF6')
@section('subtitle', $manifest['name'] ?? 'Replicated milestone')

@section('content')
<section>
    <div class="panel">
        <p class="lede">{{ $manifest['question'] ?? '' }}</p>
        <p class="verdict"><strong>{{ ($aggregate['verdict'] ?? false) ? 'Milestone passed' : 'Milestone failed' }}</strong></p>
        <p>
            Seed is the experimental replicate · {{ $summary['replication']['seeds'] ?? 0 }} paired seeds ·
            {{ number_format($aggregate['bootstrap']['resamples'] ?? 0) }} paired bootstrap resamples ·
            {{ $summary['replication']['failed_seeds'] ?? 0 }} failed seeds ·
            {{ $summary['replication']['settling_failures'] ?? 0 }} settling failures.
        </p>
    </div>
</section>

<section>
    <h2>Criterion-by-criterion verdict</h2>
    <div class="panel">
        <table>
            <thead><tr><th class="l">Criterion</th><th>Passed</th><th class="l">Evidence</th></tr></thead>
            <tbody>
            @foreach (($aggregate['criteria'] ?? []) as $name => $criterion)
                <tr>
                    <td class="l"><code>{{ $name }}</code></td>
                    <td>{{ $criterion['passed'] ? 'yes' : 'no' }}</td>
                    <td class="l"><code>{{ json_encode($criterion) }}</code></td>
                </tr>
            @endforeach
            </tbody>
        </table>
    </div>
</section>

<section>
    <h2>Paired seed effects</h2>
    @foreach (($aggregate['effects'] ?? []) as $name => $effect)
        <div class="panel" style="margin-bottom:16px">
            <h3><code>{{ $name }}</code></h3>
            <p>
                Median {{ $effect['median'] }} · 95% interval <code>{{ json_encode($effect['interval_95']) }}</code> ·
                expected direction {{ $effect['expected_direction_proportion'] }} · failures {{ $effect['failure_count'] }}
            </p>
            <p>Every seed value <code>{{ json_encode($effect['seed_values'] ?? []) }}</code></p>
        </div>
    @endforeach
</section>

<section>
    <h2>Seed audit</h2>
    @foreach (($metrics['seeds'] ?? []) as $seed)
        <div class="panel" style="margin-bottom:16px">
            <h3>Seed <code>{{ $seed['seed'] }}</code></h3>
            <p>Effects <code>{{ json_encode($seed['effects']) }}</code></p>
            <p>Settling failures {{ $seed['settling_failures'] }} · seed failures <code>{{ json_encode($seed['seed_failures']) }}</code></p>
            <details>
                <summary>Recorded values, conditions, and criteria</summary>
                <code>{{ json_encode($seed) }}</code>
            </details>
        </div>
    @endforeach
</section>
@endsection
