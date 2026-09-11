<?php

namespace Tests\Feature;

use Symfony\Component\Process\Process;
use Tests\TestCase;

/**
 * The workbench renders artifacts and computes nothing (ADR-0007). These assert what a
 * reader sees against real run directories rather than a hand-built fixture: a fixture
 * would let the page and the artifact contract drift apart without anything failing.
 *
 * Artifacts are not version-controlled, so the tests that need a current-contract run
 * skip when there is none rather than failing on a fresh clone. The tests that only
 * need the page not to fall over run against whatever is on disk.
 *
 * The superseded-architecture test builds its own old-contract artifact because no
 * future run will write one. The page must preserve such artifacts without interpreting
 * them through the current architecture.
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
        $process->mustRun();

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

    /** The newest run written against the current artifact contract, if any. */
    private function currentRun(): ?string
    {
        foreach (array_reverse($this->runs()) as $run) {
            $path = base_path('artifacts/'.$run.'/connectivity.json');
            if (! file_exists($path)) {
                continue;
            }
            $connectivity = json_decode(file_get_contents($path), true)['connectivity'] ?? [];
            if (($connectivity['model'] ?? null) === 'ncl-column-network-v1') {
                return $run;
            }
        }

        return null;
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

    public function test_a_run_page_shows_what_the_artifact_recorded(): void
    {
        $run = $this->currentRun();
        if ($run === null) {
            $this->markTestSkipped(
                'no current-contract artifact on disk; run: PYTHONPATH=ccf6-runtime/src '
                .'python3 -m ccf6 experiments/001-cardinal-recruitment.json artifacts'
            );
        }

        $summary = json_decode(file_get_contents(base_path('artifacts/'.$run.'/summary.json')), true);
        $this->get('/runs/'.$run)
            ->assertOk()
            ->assertSee('Recruitment and cardinal candidates')
            ->assertSee('Partial cues and reciprocal reactivation')
            ->assertSee(number_format($summary['overall']['columns']))
            ->assertSee(number_format($summary['overall']['shape_selectivity_max'], 4))
            ->assertSee(number_format($summary['completion']['shape_cue_concept_similarity'], 4));
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

    public function test_a_run_from_a_superseded_architecture_says_so_rather_than_failing(): void
    {
        $root = sys_get_temp_dir().'/ccf6-superseded-'.getmypid();
        $run = '001-20260907T205400-7f76d3f788715d4d';
        mkdir($root.'/'.$run, 0777, true);

        // Any connectivity record without the current model contract is historical.
        file_put_contents($root.'/'.$run.'/connectivity.json', json_encode([
            'connectivity' => ['areas' => ['colour' => ['levels' => 3]]],
            'palette' => ['white', 'red'],
        ]));
        file_put_contents($root.'/'.$run.'/manifest.json', json_encode([
            'name' => 'Colour selectivity baseline',
            'kind' => 'colour_selectivity_baseline',
            'started' => '2026-09-07T20:54:00+00:00',
        ]));
        file_put_contents($root.'/'.$run.'/summary.json', json_encode(['overall' => []]));

        try {
            config(['ccf6.artifact_root' => $root]);
            $this->get('/runs/'.$run)->assertOk()->assertSee('predates the current architecture');
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
