import { Package, PhylumApi } from "phylum";

// Ensure required arguments are present.
const args = Deno.args.slice(0);
if (args.length < 4) {
    console.error(
        "Usage: phylum ci <PROJECT> <LABEL> [--group <GROUP>] <BASE> <DEPFILE:TYPE...>",
    );
    Deno.exit(1);
}

// Find optional groups argument.
let group = undefined;
const groupArgsIndex = args.indexOf("--group");
if (groupArgsIndex != -1) {
    const groupArgs = args.splice(groupArgsIndex, 2);
    group = groupArgs[1];
}

// Parse remaining arguments.
const project = args[0];
const label = args[1];
const base = args[2];
const depfiles = args.splice(3);

// Parse new dependency files.
let packages: Package[] = [];
for (const depfile of depfiles) {
    const depfile_path = depfile.substring(0, depfile.lastIndexOf(":"));
    const depfile_type = depfile.substring(depfile.lastIndexOf(":") + 1, depfile.length);
    const depfileDeps = await PhylumApi.parseLockfile(depfile_path, depfile_type);
    packages = packages.concat(depfileDeps.packages);
}

// Deserialize base dependencies.
const baseDepsJson = await Deno.readTextFile(base);
const baseDeps = JSON.parse(baseDepsJson);

// Short-circuit if there are no dependencies.
if (packages.length == 0) {
    console.log("{}");
    Deno.exit(0);
}

// Submit analysis job.
const jobID = await PhylumApi.analyze(
    packages,
    project,
    group,
    label,
);

// Get analysis job results.
const jobStatus = await PhylumApi.getJobStatus(jobID, baseDeps);

// Output results as JSON.
console.log(JSON.stringify(jobStatus));
