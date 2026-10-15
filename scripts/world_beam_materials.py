"""World-model materials for the 12m / 30m beams; no character-local mask.

Reuse the native shader/settings already used by the bloodsea boundary. The
beams need the entire mesh, so its annulus-only UV gradient stays disabled.
IDs retain the exact pair viewed in the October 14 AllSpark material control.
"""
import copy

from sword_cultivator_spec import guid


def material_id(style, shape='sword'):
    if style not in ('tianqing', 'taixuan') or shape not in ('sword', 'circle'):
        raise ValueError('World beam materials belong only to the two beam styles')
    index = 0 if shape == 'sword' else 1
    return guid(f'vfx/preview/nifeng/world-model-control/material/{index}')


def material_nodes():
    from xuehai_boundary_visual_polish import documents
    donor = documents()['Material'].find('./region/node/children/node[@id="Resource"]')
    result = []
    for index, shape in enumerate(('sword', 'circle')):
        node = copy.deepcopy(donor)
        for key, value in (('ID', material_id('tianqing', shape)),
                           ('Name', 'ESC_Nifeng_WorldControl_' + ('Core' if index == 0 else 'Halo'))):
            node.find(f'./attribute[@id="{key}"]').set('value', value)
        for name, value in (('_Use_ProceduralGradientForMask', '0'),
                            ('Opacity_Mult', '1' if index == 0 else '0.25')):
            parameter, = [n for n in node.findall('./children/node')
                          if n.find(f'./attribute[@id="ParameterName"][@value="{name}"]') is not None]
            parameter.find('./attribute[@id="Enabled"]').set('value', 'True')
            parameter.find('./attribute[@id="Value"]').set('value', value)
        result.append(node)
    return result
