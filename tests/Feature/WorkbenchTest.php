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
 * need the page not to fall over run against whatever is on disk, including runs from
 * a superseded architecture.
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
        foreach ($this->runs() as $run) {
            $path = base_path('artifacts/'.$run.'/connectivity.json');
            $connectivity = file_exists($path)
                ? json_decode(file_get_contents($path), true)['connectivity'] ?? []
                : [];
            if (! array_key_exists('structures', $connectivity)) {
                $this->get('/runs/'.$run)->assertOk()->assertSee('predates the current architecture');

                return;
            }
        }
        $this->markTestSkipped('no superseded artifact on disk');
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
