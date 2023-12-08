import { Package, PackageWithOrigin, PhylumApi } from "phylum";

// Ensure required arguments are present.
const args = Deno.args.slice(0);
if (args.length < 4) {
    console.error(
        "Usage: phylum ci <PROJECT> <LABEL> [--group <GROUP>] <BASE> <CURRENT>",
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
const current = args[3];

// Deserialize current dependencies.
const currDepsJson = await Deno.readTextFile(current);
const currDeps: PackageWithOrigin[] = JSON.parse(currDepsJson);

// Short-circuit if there are no current dependencies.
if (currDeps.length == 0) {
    console.log("{}");
    Deno.exit(0);
}

// Deserialize base dependencies.
const baseDepsJson = await Deno.readTextFile(base);
const baseDeps: Package[] = JSON.parse(baseDepsJson);

// Submit analysis job.
const jobID = await PhylumApi.analyze(
    currDeps,
    project,
    group,
    label,
);

// Get analysis job results.
const jobStatus = await PhylumApi.getJobStatus(jobID, baseDeps);

// Output results as JSON.
console.log(JSON.stringify(jobStatus));
