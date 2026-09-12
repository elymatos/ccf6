<?php

namespace Tests\Feature;

use Symfony\Component\Process\Process;
use Tests\TestCase;

/**
 * The workbench renders artifacts and computes nothing (ADR-0007). These assert what a
 * reader sees against real run directories rather than a hand-built fixture: a fixture
 * would let the page and the artifact contract drift apart without anything failing.
 *
 * Unsupported and malformed artifacts are built as fixtures because the runtime must
 * never emit them. The workbench preserves their files without inventing results.
 */
class WorkbenchTest extends TestCase
{
    /** @return list<string> */
    private function runs(): array
    {
        return array_map('basename', glob(base_path('artifacts').'/*', GLOB_ONLYDIR) ?: []);
    }

    /** @return array{string, string} */
    private function runExperiment(string $experiment): array
    {
        return $this->runExperimentPath(base_path('experiments/'.$experiment));
    }

    /** @return array{string, string} */
    private function runExperimentPath(string $experiment): array
    {
        $root = sys_get_temp_dir().'/ccf6-'.pathinfo($experiment, PATHINFO_FILENAME).'-'.getmypid();
        $process = new Process(
            ['python3', '-m', 'ccf6', $experiment, $root],
            base_path(),
            ['PYTHONPATH' => base_path('ccf6-runtime/src')],
        );
        $process->setTimeout(300)->mustRun();

        return [$root, basename(glob($root.'/*', GLOB_ONLYDIR)[0])];
    }

    private function removeArtifactRoot(string $root, string $run): void
    {
        foreach (glob($root.'/'.$run.'/*') as $file) {
            unlink($file);
        }
        rmdir($root.'/'.$run);
        rmdir($root);
    }

    public function test_it_lists_every_run_on_disk(): void
    {
        $response = $this->get('/')->assertOk();
        foreach ($this->runs() as $run) {
            $response->assertSee($run, false);
        }
    }

    public function test_every_run_on_disk_renders(): void
    {
        foreach ($this->runs() as $run) {
            $this->get('/runs/'.$run)->assertOk();
        }
        $this->addToAssertionCount(1);
    }

    public function test_the_generated_lexical_grounding_domain_is_rendered_without_recomputation(): void
    {
        [$root, $run] = $this->runExperiment('002-synthetic-lexical-grounding.json');
        $dataset = json_decode(file_get_contents($root.'/'.$run.'/dataset.json'), true);

        try {
            config(['ccf6.artifact_root' => $root]);
            $this->get('/runs/'.$run)
                ->assertSee('Synthetic lexical-grounding domain')
                ->assertSee('Constraint checks')
                ->assertSee($dataset['categories'][0]['id'])
                ->assertSee($dataset['pseudowords'][0]['id'])
                ->assertSee('64 pairings');
        } finally {
            $this->removeArtifactRoot($root, $run);
        }
    }

    public function test_zero_rest_network_renders_settling_and_actual_connectivity(): void
    {
        [$root, $run] = $this->runExperiment('003-zero-rest-network.json');
        $topology = json_decode(file_get_contents($root.'/'.$run.'/topology.json'), true);

        try {
            config(['ccf6.artifact_root' => $root]);
            $this->get('/runs/'.$run)
                ->assertSee('Settled successfully')
                ->assertSee('Max-tick failure')
                ->assertSee('Input, Integration, and Output')
                ->assertSee($topology['projections'][0]['id'])
                ->assertSee((string) $topology['projections'][0]['endpoints'][0]['source_column'])
                ->assertSee(number_format($topology['projections'][0]['endpoints'][0]['ascending_weight'], 6));
        } finally {
            $this->removeArtifactRoot($root, $run);
        }
    }

    public function test_coordinated_presentations_render_order_trajectories_and_failures(): void
    {
        [$root, $run] = $this->runExperiment('004-coordinated-presentation.json');
        $presentations = file($root.'/'.$run.'/presentations.jsonl', FILE_IGNORE_NEW_LINES);
        $first = json_decode($presentations[0], true);

        try {
            config(['ccf6.artifact_root' => $root]);
            $this->get('/runs/'.$run)
                ->assertSee('Presentation trajectories')
                ->assertSee('Sequence-sensitive: pass')
                ->assertSee($first['id'])
                ->assertSee($first['samples'][0]['id'])
                ->assertSee($first['samples'][1]['id'])
                ->assertSee($first['samples'][1]['duration_ticks'].' ticks')
                ->assertSee('Settling failures');
        } finally {
            $this->removeArtifactRoot($root, $run);
        }
    }

    public function test_success_gated_learning_effects_are_inspectable(): void
    {
        [$root, $run] = $this->runExperiment('005-success-gated-learning.json');
        $learning = json_decode(file_get_contents($root.'/'.$run.'/learning.json'), true);
        $successful = $learning['presentations'][0];
        $unsuccessful = $learning['presentations'][1];

        try {
            config(['ccf6.artifact_root' => $root]);
            $this->get('/runs/'.$run)
                ->assertSee('Success-gated learning')
                ->assertSee('Balanced acquisition: yes')
                ->assertSee($successful['presentation_id'])
                ->assertSee('Success Signal 1.0')
                ->assertSee($unsuccessful['presentation_id'])
                ->assertSee('Success Signal 0.0')
                ->assertSee('No durable change')
                ->assertSee($successful['projections'][0]['id'])
                ->assertSee('Pre/post directional weights');
        } finally {
            $this->removeArtifactRoot($root, $run);
        }
    }

    public function test_recruitment_homeostasis_and_frozen_evaluation_are_inspectable(): void
    {
        [$root, $run] = $this->runExperiment('006-recruitment-homeostasis.json');
        $learning = json_decode(file_get_contents($root.'/'.$run.'/learning.json'), true);
        $finalPopulation = $learning['presentations'][23]['populations'][0];
        $contributor = collect($finalPopulation['contributing_presentations'])->flatten()->first();

        try {
            config(['ccf6.artifact_root' => $root]);
            $this->get('/runs/'.$run)
                ->assertSee('Recruitment and homeostasis')
                ->assertSee('Recruited Columns')
                ->assertSee($finalPopulation['id'])
                ->assertSee($contributor)
                ->assertSee('Threshold history')
                ->assertSee('Frozen evaluation')
                ->assertSee('No durable changes');
        } finally {
            $this->removeArtifactRoot($root, $run);
        }
    }

    public function test_matched_arms_and_frozen_target_basins_are_comparable(): void
    {
        [$root, $run] = $this->runExperiment('007-matched-target-basins.json');
        $arms = json_decode(file_get_contents($root.'/'.$run.'/arms.json'), true);
        $basins = json_decode(file_get_contents($root.'/'.$run.'/basins.json'), true);
        $category = array_key_first($basins['arms']['trained']['frozen']['categories']);

        try {
            config(['ccf6.artifact_root' => $root]);
            $this->get('/runs/'.$run)
                ->assertSee('Matched experimental arms')
                ->assertSee($arms['arms'][0]['initial_topology_digest'])
                ->assertSee('Frozen Target Basins')
                ->assertSee($category)
                ->assertSee('Reliable mask')
                ->assertSee('Pooled scale')
                ->assertSee('Frozen margin')
                ->assertSee('Held-out basin evaluations');
        } finally {
            $this->removeArtifactRoot($root, $run);
        }
    }

    public function test_frozen_completion_and_ordered_reactivation_evidence_is_rendered(): void
    {
        [$root, $run] = $this->runExperiment('008-completion-reactivation.json');
        $evaluation = json_decode(file_get_contents($root.'/'.$run.'/evaluation.json'), true);
        $partial = $evaluation['arms']['trained']['conditions']['partial_visual'][0];
        $lexical = $evaluation['arms']['trained']['lexical_reactivation'][0];

        try {
            config(['ccf6.artifact_root' => $root]);
            $this->get('/runs/'.$run)
                ->assertSee('Frozen cue completion')
                ->assertSee('standardized_euclidean')
                ->assertSee('cosine_distance')
                ->assertSee($partial['id'])
                ->assertSee('Ordered lexical reactivation')
                ->assertSee($lexical['pseudoword_id'])
                ->assertSee('Settling failures count as failures');
        } finally {
            $this->removeArtifactRoot($root, $run);
        }
    }

    public function test_functional_web_evidence_and_negative_result_are_rendered(): void
    {
        [$root, $run] = $this->runExperiment('009-functional-web-detection.json');
        $webs = json_decode(file_get_contents($root.'/'.$run.'/webs.json'), true);
        $category = array_key_first($webs['webs']);
        $column = array_key_first($webs['webs'][$category]['columns']);

        try {
            config(['ccf6.artifact_root' => $root]);
            $this->get('/runs/'.$run)
                ->assertSee('Causal Functional Web detection')
                ->assertSee($category)
                ->assertSee($column)
                ->assertSee('Reliability')
                ->assertSee('Causal completion contribution')
                ->assertSee('Reciprocal effective connectivity')
                ->assertSee('No Functional Web detected')
                ->assertSee('held-out used: no');
        } finally {
            $this->removeArtifactRoot($root, $run);
        }
    }

    public function test_cardinal_evidence_controls_and_negative_result_are_rendered(): void
    {
        [$root, $run] = $this->runExperiment('010-cardinal-classification.json');
        $cardinals = json_decode(file_get_contents($root.'/'.$run.'/cardinals.json'), true);
        $category = array_key_first($cardinals['categories']);

        try {
            config(['ccf6.artifact_root' => $root]);
            $this->get('/runs/'.$run)
                ->assertSee('Cardinal causal classification')
                ->assertSee($category)
                ->assertSee('Cardinal Candidates')
                ->assertSee('Median full-presentation Output')
                ->assertSee('Individual and group Lesions')
                ->assertSee('No Cardinal Candidate classified')
                ->assertSee('pending_multi_seed_experiment');
        } finally {
            $this->removeArtifactRoot($root, $run);
        }
    }

    public function test_detailed_cortical_processes_render_actual_population_and_pathway_trajectories(): void
    {
        [$root, $run] = $this->runExperiment('012-detailed-cortical-circuit.json');
        $topology = json_decode(file_get_contents($root.'/'.$run.'/topology.json'), true);
        $activity = json_decode(file_get_contents($root.'/'.$run.'/activity.json'), true);

        try {
            config(['ccf6.artifact_root' => $root]);
            $this->get('/runs/'.$run)
                ->assertSee('Explicit laminar cortical circuit')
                ->assertSee('Actual runtime trajectories')
                ->assertSee($topology['populations']['A.L4Pyr']['legacy_name'])
                ->assertSee($topology['pathways'][0]['id'])
                ->assertSee(array_key_first($activity['processes']))
                ->assertSee('Release facilitation')
                ->assertSee('STDP postponed');
        } finally {
            $this->removeArtifactRoot($root, $run);
        }
    }

    public function test_replicated_milestone_verdict_renders_every_seed_and_criterion(): void
    {
        $root = sys_get_temp_dir().'/ccf6-replicated-'.getmypid();
        $run = '011-test-replicated';
        mkdir($root.'/'.$run, 0777, true);
        $files = [
            'definition.json', 'manifest.json', 'dataset.json', 'topology.npz',
            'presentations.jsonl', 'learning.npz', 'activity.npz', 'basins.json',
            'webs.json', 'cardinals.json', 'metrics.json', 'aggregate.json', 'summary.json',
        ];
        file_put_contents($root.'/'.$run.'/manifest.json', json_encode([
            'contract' => 'ncl-functional-web-v1',
            'kind' => 'replicated_milestone',
            'name' => 'Replicated Functional Web milestone verdict',
            'question' => 'Does the milestone pass?',
            'digest' => 'fixture-identity',
            'software_version' => '0.2.0',
            'status' => 'completed',
            'files' => $files,
        ]));
        foreach (['definition.json', 'dataset.json', 'basins.json', 'webs.json', 'cardinals.json'] as $file) {
            file_put_contents($root.'/'.$run.'/'.$file, '{}');
        }
        foreach (['topology.npz', 'learning.npz', 'activity.npz'] as $file) {
            file_put_contents($root.'/'.$run.'/'.$file, 'fixture');
        }
        file_put_contents($root.'/'.$run.'/presentations.jsonl', "{\"seed\":20260910}\n");
        file_put_contents($root.'/'.$run.'/summary.json', json_encode([
            'replication' => ['seeds' => 20, 'bootstrap_resamples' => 10000, 'failed_seeds' => 1, 'settling_failures' => 2],
            'milestone_verdict' => false,
        ]));
        file_put_contents($root.'/'.$run.'/metrics.json', json_encode([
            'replicate_unit' => 'seed',
            'seeds' => [[
                'seed' => 20260910,
                'effects' => ['completion' => 0.0],
                'settling_failures' => 2,
                'seed_failures' => ['candidate_stimulation_and_lesion_not_executable'],
            ]],
        ]));
        file_put_contents($root.'/'.$run.'/aggregate.json', json_encode([
            'bootstrap' => ['resamples' => 10000, 'seed' => 20260910],
            'effects' => ['completion' => ['median' => 0.0, 'interval_95' => [0.0, 0.0], 'expected_direction_proportion' => 0.0, 'failure_count' => 0]],
            'criteria' => ['completion_improvement' => ['passed' => false, 'evidence' => 'interval']],
            'verdict' => false,
        ]));
        $manifest = json_decode(file_get_contents($root.'/'.$run.'/manifest.json'), true);
        $manifest['checksums'] = [];
        foreach ($files as $file) {
            if ($file !== 'manifest.json') {
                $manifest['checksums'][$file] = hash_file('sha256', $root.'/'.$run.'/'.$file);
            }
        }
        file_put_contents($root.'/'.$run.'/manifest.json', json_encode($manifest));

        try {
            config(['ccf6.artifact_root' => $root]);
            $this->get('/runs/'.$run)
                ->assertSee('Replicated Functional Web milestone verdict')
                ->assertSee('Milestone failed')
                ->assertSee('Complete artifact contract')
                ->assertSee('topology.npz')
                ->assertSee('fixture-identity')
                ->assertSee('completion_improvement')
                ->assertSee('candidate_stimulation_and_lesion_not_executable')
                ->assertSee('10,000 paired bootstrap resamples')
                ->assertSee('Seed is the experimental replicate');
        } finally {
            $this->removeArtifactRoot($root, $run);
        }
    }

    public function test_zero_rest_network_identifies_a_max_tick_failure(): void
    {
        $definitionPath = sys_get_temp_dir().'/ccf6-failing-network-'.getmypid().'.json';
        $definition = json_decode(file_get_contents(base_path('experiments/003-zero-rest-network.json')), true);
        $definition['network']['settling'] = [
            'epsilon' => 1.0,
            'stable_ticks' => 3,
            'max_ticks' => 2,
        ];
        file_put_contents($definitionPath, json_encode($definition));
        [$root, $run] = $this->runExperimentPath($definitionPath);

        try {
            config(['ccf6.artifact_root' => $root]);
            $this->get('/runs/'.$run)
                ->assertSee('Settling failed at max ticks')
                ->assertSee('Max-tick failure')
                ->assertSee('yes');
        } finally {
            $this->removeArtifactRoot($root, $run);
            unlink($definitionPath);
        }
    }

    public function test_an_unsupported_artifact_is_reported_without_interpretation(): void
    {
        $root = sys_get_temp_dir().'/ccf6-unsupported-'.getmypid();
        $run = '001-20260907T205400-7f76d3f788715d4d';
        mkdir($root.'/'.$run, 0777, true);

        file_put_contents($root.'/'.$run.'/manifest.json', json_encode([
            'contract' => 'unknown-contract-v0',
            'name' => 'External result',
            'kind' => 'external_result',
            'started' => '2026-09-07T20:54:00+00:00',
            'files' => ['manifest.json', 'payload.json'],
        ]));
        file_put_contents($root.'/'.$run.'/payload.json', '{}');

        try {
            config(['ccf6.artifact_root' => $root]);
            $this->get('/runs/'.$run)
                ->assertOk()
                ->assertSee('Unsupported or malformed artifact')
                ->assertSee('contract is unsupported');
        } finally {
            array_map('unlink', glob($root.'/'.$run.'/*'));
            rmdir($root.'/'.$run);
            rmdir($root);
        }
    }

    public function test_a_malformed_current_artifact_reports_the_missing_file(): void
    {
        $root = sys_get_temp_dir().'/ccf6-malformed-'.getmypid();
        $run = '011-malformed';
        mkdir($root.'/'.$run, 0777, true);
        file_put_contents($root.'/'.$run.'/manifest.json', json_encode([
            'contract' => 'ncl-functional-web-v1',
            'kind' => 'replicated_milestone',
            'digest' => 'malformed-fixture',
            'software_version' => '0.2.0',
            'status' => 'completed',
            'files' => [
                'definition.json', 'manifest.json', 'dataset.json', 'topology.npz',
                'presentations.jsonl', 'learning.npz', 'activity.npz', 'basins.json',
                'webs.json', 'cardinals.json', 'metrics.json', 'aggregate.json', 'summary.json',
            ],
            'checksums' => array_fill_keys([
                'definition.json', 'dataset.json', 'topology.npz', 'presentations.jsonl',
                'learning.npz', 'activity.npz', 'basins.json', 'webs.json',
                'cardinals.json', 'metrics.json', 'aggregate.json', 'summary.json',
            ], 'missing'),
        ]));

        try {
            config(['ccf6.artifact_root' => $root]);
            $this->get('/runs/'.$run)
                ->assertOk()
                ->assertSee('Unsupported or malformed artifact')
                ->assertSee('definition.json is missing');
        } finally {
            array_map('unlink', glob($root.'/'.$run.'/*'));
            rmdir($root.'/'.$run);
            rmdir($root);
        }
    }

    public function test_a_missing_run_is_a_404(): void
    {
        $this->get('/runs/does-not-exist')->assertNotFound();
    }

    public function test_it_renders_a_project_document(): void
    {
        $this->get('/docs/architecture')->assertOk()->assertSee('Web');
    }
}
