package io.kestra.plugin.ansible.runner;

import io.kestra.core.models.property.Property;
import io.kestra.core.runners.RunContext;
import io.kestra.core.runners.RunContextFactory;
import io.kestra.core.utils.IdUtils;
import io.kestra.plugin.ansible.runner.models.Project;
import io.kestra.plugin.ansible.runner.utils.ArchiveUtils;
import io.micronaut.test.extensions.junit5.annotation.MicronautTest;
import jakarta.inject.Inject;
import org.junit.jupiter.api.Test;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;

import static org.hamcrest.MatcherAssert.assertThat;
import static org.hamcrest.Matchers.containsString;
import static org.junit.jupiter.api.Assertions.assertThrows;

@MicronautTest
class AnsibleRunnerSecurityTest {

    @Inject
    private RunContextFactory runContextFactory;

    @Test
    void testShellInjectionIsBlocked() {
        AnsibleRunner task = AnsibleRunner.builder()
            .id(IdUtils.create())
            .type(AnsibleRunner.class.getName())
            .pythonDependencies(Property.of(List.of("-r requirements.txt")))
            .project(Project.builder().inline(Property.of("- hosts: localhost\n  tasks:\n    - debug: msg=ok")).build())
            .build();

        RunContext runContext = runContextFactory.of();
        IllegalArgumentException e = assertThrows(IllegalArgumentException.class, () -> task.run(runContext));
        assertThat(e.getMessage(), containsString("Invalid python dependency"));
    }

    @Test
    void testValidVersionPinsAllowed() throws Exception {
        AnsibleRunner task = AnsibleRunner.builder()
            .id(IdUtils.create())
            .type(AnsibleRunner.class.getName())
            .pythonDependencies(Property.of(List.of("ansible==2.9.0", "boto3>=1.15.0")))
            .project(Project.builder().inline(Property.of("- hosts: localhost\n  tasks:\n    - debug: msg=ok")).build())
            .build();

        RunContext runContext = runContextFactory.of();
        try {
            task.run(runContext);
        } catch (IllegalArgumentException e) {
            if (e.getMessage().contains("Invalid python dependency")) {
                throw new AssertionError("Valid versions were rejected", e);
            }
        } catch (Exception ignored) {}
    }

    @Test
    void testPathTraversalBlocked() {
        AnsibleRunner task = AnsibleRunner.builder()
            .id(IdUtils.create())
            .type(AnsibleRunner.class.getName())
            .inventoryFile(Property.of("../../etc/passwd"))
            .project(Project.builder().inline(Property.of("- hosts: all")).build())
            .build();

        RunContext runContext = runContextFactory.of();
        IllegalArgumentException e = assertThrows(IllegalArgumentException.class, () -> task.run(runContext));
        assertThat(e.getMessage(), containsString("Path traversal blocked"));
    }

    @Test
    void testSymlinkZipSlipBlocked() throws IOException {
        Path tempDir = Files.createTempDirectory("zipslip-test");
        Path zipPath = tempDir.resolve("malicious.zip");

        Path sourceDir = tempDir.resolve("source");
        Files.createDirectories(sourceDir);
        Path linkPath = sourceDir.resolve("link");
        try {
            Files.createSymbolicLink(linkPath, tempDir.resolve("nonexistent"));
            IOException e = assertThrows(IOException.class, () -> ArchiveUtils.zipDirectory(sourceDir, zipPath));
            assertThat(e.getMessage(), containsString("Symlinks are not allowed"));
        } catch (UnsupportedOperationException ignored) {
            // OS doesn't support symlinks
        }
    }

    @Test
    void testMissingStatusFileDefaultsToFailed() throws Exception {
        AnsibleRunner task = AnsibleRunner.builder()
            .id(IdUtils.create())
            .type(AnsibleRunner.class.getName())
            .project(Project.builder().inline(Property.of("- hosts: localhost")).build())
            .taskRunner(new MockRunnerMissingStatus())
            .build();

        RunContext runContext = runContextFactory.of();
        RuntimeException e = assertThrows(RuntimeException.class, () -> task.run(runContext));
        assertThat(e.getMessage(), containsString("failed"));
    }

    public static class MockRunnerMissingStatus extends io.kestra.core.models.tasks.runners.TaskRunner<io.kestra.core.models.tasks.runners.TaskRunnerDetailResult> {
        public MockRunnerMissingStatus() {
            super();
        }
        @Override
        public io.kestra.core.models.tasks.runners.TaskRunnerResult<io.kestra.core.models.tasks.runners.TaskRunnerDetailResult> run(RunContext runContext, io.kestra.core.models.tasks.runners.TaskCommands taskCommands, List<String> filesToDownload) throws Exception {
            return new io.kestra.core.models.tasks.runners.TaskRunnerResult<>(0, null);
        }
    }
}
