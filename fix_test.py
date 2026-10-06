import re

with open("src/test/java/io/kestra/plugin/ansible/runner/AnsibleRunnerComprehensiveTest.java", "r") as f:
    content = f.read()

# Replace all occurrences of env_backup with env, EXCEPT inside the MockDocker.run method where it creates the backup.
# Actually, inside MockDocker.run, we can STILL create env_backup just so the test asserts can inspect it,
# but we MUST add an assertion at the end of every test method that `runner/env` is deleted.
# Let's add the assertion at the end of test methods.

# Let's find all occurrences of:
# AnsibleRunner.Output output = task.run(runContext);
# and append `assertFalse(Files.exists(runContext.workingDir().path().resolve("runner/env")), "env directory must be deleted");`

content = re.sub(
    r'(AnsibleRunner\.Output output = task\.run\(runContext(?:Zero)?\);)',
    r'\1\n        assertFalse(Files.exists(runContext.workingDir().path().resolve("runner/env")), "env directory must be deleted");',
    content
)

# And also inside testMissingStatusFileDefaultsToFailed, which we just added in another file, but let's make sure ComprehensiveTest passes.

with open("src/test/java/io/kestra/plugin/ansible/runner/AnsibleRunnerComprehensiveTest.java", "w") as f:
    f.write(content)

