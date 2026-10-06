import re

with open("src/test/java/io/kestra/plugin/ansible/runner/AnsibleRunnerSecurityTest.java", "r") as f:
    content = f.read()

content = content.replace("List.of(\"-r requirements.txt\")", "io.kestra.core.models.property.Property.of(List.of(\"-r requirements.txt\"))")
content = content.replace("List.of(\"ansible==2.9.0\", \"boto3>=1.15.0\")", "io.kestra.core.models.property.Property.of(List.of(\"ansible==2.9.0\", \"boto3>=1.15.0\"))")
content = content.replace("inline(\"- hosts: localhost\\n  tasks:\\n    - debug: msg=ok\")", "inline(io.kestra.core.models.property.Property.of(\"- hosts: localhost\\n  tasks:\\n    - debug: msg=ok\"))")
content = content.replace("inline(\"- hosts: all\")", "inline(io.kestra.core.models.property.Property.of(\"- hosts: all\"))")
content = content.replace("inline(\"- hosts: localhost\")", "inline(io.kestra.core.models.property.Property.of(\"- hosts: localhost\"))")
content = content.replace("inventoryFile(\"../../etc/passwd\")", "inventoryFile(io.kestra.core.models.property.Property.of(\"../../etc/passwd\"))")

# Fix MockDocker usage
content = content.replace(
    ".taskRunner(new AnsibleRunnerComprehensiveTest.MockDocker(false, false, false, false))",
    ".taskRunner(new MockDockerMissingStatus())"
)

# Append MockDockerMissingStatus
content = content.replace("}", """
    public static class MockDockerMissingStatus extends io.kestra.plugin.scripts.exec.scripts.runners.Docker {
        @Override
        public io.kestra.plugin.scripts.exec.scripts.runners.RunnerResult run(io.kestra.plugin.scripts.exec.scripts.runners.CommandsWrapper commandsWrapper) throws Exception {
            return new io.kestra.plugin.scripts.exec.scripts.runners.RunnerResult(0, null);
        }
    }
}
""")

with open("src/test/java/io/kestra/plugin/ansible/runner/AnsibleRunnerSecurityTest.java", "w") as f:
    f.write(content)

