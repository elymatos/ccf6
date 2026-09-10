"""Presentation behavior at the experimental boundary."""

from ccf6 import figures
from ccf6.ego import Presentation
from ccf6.world import World


def test_a_presentation_samples_every_part_of_a_figure():
    world = World(12)
    shape = figures.FIGURES["T"]
    world.place_object(shape, (5, 5))
    presentation = Presentation.of_object(world, shape, (5, 5))
    assert len(presentation.samples) == len(shape.parts)


def test_sample_order_is_declared_and_reproducible():
    world = World(12)
    shape = figures.FIGURES["T"]
    world.place_object(shape, (5, 5))
    first = Presentation.of_object(world, shape, (5, 5), "nearest")
    second = Presentation.of_object(world, shape, (5, 5), "nearest")
    assert first == second


def test_the_same_figure_has_the_same_sample_colours_at_another_origin():
    world = World(12)
    shape = figures.FIGURES["T"]
    colours = []
    for origin in ((2, 2), (6, 6)):
        world.clear()
        world.place_object(shape, origin)
        presentation = Presentation.of_object(world, shape, origin)
        colours.append([sample.colour for sample in presentation.samples])
    assert colours[0] == colours[1]


def test_an_empty_presentation_is_valid():
    assert Presentation.over(World(8), [], "raster").samples == []
