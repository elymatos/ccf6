<?php

namespace Tests\Feature;

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
 * The superseded-architecture test is the exception. Runs from the previous substrate
 * were deleted once they became confusing, and no future run will be written against an
 * old contract, so nothing on disk exercises that path any more. It builds its own run
 * directory instead. What it asserts is that a connectivity record without `structures`
 * is reported rather than drawn, and that claim is about the contract, not about any
 * particular old run.
 */
class WorkbenchTest extends TestCase
{
    /** @return list<string> */
    private function runs(): array
    {
        return array_map('basename', glob(base_path('artifacts').'/*', GLOB_ONLYDIR) ?: []);
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
            if (array_key_exists('structures', $connectivity)) {
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
                .'python3 -m ccf6 experiments/004-structure-baseline.json artifacts'
            );
        }

        $summary = json_decode(file_get_contents(base_path('artifacts/'.$run.'/summary.json')), true);
        $this->get('/runs/'.$run)
            ->assertOk()
            ->assertSee('The Web')
            ->assertSee('The Schema')
            ->assertSee('The Index')
            ->assertSee((string) $summary['overall']['columns'])
            ->assertSee(number_format($summary['overall']['shape_selectivity_max'], 4))
            ->assertSee(number_format($summary['schema']['path_consistency_error'], 9));
    }

    public function test_a_run_from_a_superseded_architecture_says_so_rather_than_failing(): void
    {
        $root = sys_get_temp_dir().'/ccf6-superseded-'.getmypid();
        $run = '001-20260907T205400-7f76d3f788715d4d';
        mkdir($root.'/'.$run, 0777, true);

        // The shape an artifact had before the Web, Schema and Index existed: Areas
        // instead of structures. The absence of `structures` is the whole signal.
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
