"""Parser contracts only; synthetic logs cannot establish editor acceptance."""
import importlib.util
import unittest
from pathlib import Path

SCRIPT=Path(__file__).resolve().parents[1]/'analyze-sword-toolkit-log.py'
spec=importlib.util.spec_from_file_location('esc_toolkit_analyzer',SCRIPT)
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ToolkitLogAnalyzer(unittest.TestCase):
    def analyze(self,*lines): return module.analyze_lines(lines,Path('sample.log'))

    def test_duplicate_noesis_report_is_one_issue_with_all_line_evidence(self):
        path='Assets/Shared/Resources/Highlight/ESC_SwordYuan.png'
        report=self.analyze("!ASSERT!UI: Metadata not found for texture! "+path,
            "!ASSERT!UI: Image not found '"+path+"'", "Couldn't find the file "+path)
        self.assertEqual(len(report['ModuleIssues']),1)
        issue=report['ModuleIssues'][0]
        self.assertEqual((issue['kind'],issue['identity'],issue['occurrences']),('missing_image',path,3))
        self.assertEqual([row['line'] for row in issue['evidence']],[1,2,3])
        self.assertEqual({row['path'] for row in issue['evidence']},{'sample.log'})

    def test_tooltip_and_status_mapping_are_directly_attributed(self):
        report=self.analyze(
            "!ASSERT!Code: Stats description parameters do not support functors with conditions 'IF(...)'. (Spell ID: Projectile_ESC_taixuan_zhaoxi)",
            'No UUID condition error object is configured for error with name: CE_Status_ESC_MAIN_SWORD_False')
        self.assertEqual({row['kind'] for row in report['ModuleIssues']},
                         {'conditional_tooltip_damage','missing_condition_error_mapping'})
        self.assertEqual(report['ModuleErrorGate'],'fail')

    def test_vanilla_noise_is_not_mod_error_but_crash_fails_editor_gate(self):
        report=self.analyze('!ASSERT!Code: Failed to find resource for Genome global function e5ba5536',
            'CLIENT STATE SWAP - from: StopLoading, to: Exit',
            '!CRITICAL!ASSERT!Code: EoCPlugin.dll',
            'Exception Type: EXCEPTION_ACCESS_VIOLATION',
            'StackTrace:',
            'Noesis::BaseObject::operator delete',
            'ls::ResourceManager::UninstallGameUI')
        self.assertEqual(report['ModuleIssues'],[])
        self.assertEqual(report['ModuleErrorGate'],'no-attributable-errors-observed')
        self.assertEqual(report['ProcessExitGate'],'fail-native-crash')
        self.assertEqual(report['NativeCrash']['Attribution'],'unresolved')
        self.assertEqual(report['ToolkitLogGate'],'fail')
        self.assertEqual([row['line'] for row in report['NativeCrash']['RelevantStackFrames']],[6,7])

    def test_clean_log_only_satisfies_log_gate(self):
        report=self.analyze('ServerLoadProtocol: Loaded EasternSwordCultivator',
            'Image registered: Assets/Shared/Resources/ESC_SwordYuan.png')
        self.assertEqual(report['ToolkitLogGate'],'no-attributable-errors-observed')
        self.assertIn('no Toolkit or game behavior',report['Boundary'])


if __name__=='__main__': unittest.main()
