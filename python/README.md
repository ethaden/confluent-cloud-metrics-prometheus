# Prometheus exporter for Confluent Cloud Service Quota API

This is an experimental implementation of a Prometheus exporter which fetches usage and limits from the Service Quote API from Confluent Cloud and makes them available to Prometheus. The tool handles the pagination and rate limits of the Confluent Cloud API properly and supports sophisticated authentication via Azure EntraID in addition to classical API key authentication.

## Configuration

Copy the `example-config.yaml` to `config.yaml` and customize it. For the Azure-specific settings, see below.

### Authentication

You have two options: You can use a cloud or global API key, or configure OIDC in Azure EntraID.
Variables can be read from environment variables, please see the example file for details.

If you want to use basic authentication, provide an API for a service account with the "OrganizationAdmin" role in Confluent Cloud for full visibility. You can use a service account with less permissions, too, but would not see all values.

If you use OIDC with Azure, you have multiple options. First, follow the Confluent documentation in order to set up your infrastructure properly. Configure an identity pool in Confluent Cloud which e.g. checks for membership in an "Confluent Cloud Admin" (you can name it as you like) security group in your EntraID tenant. Assign "OrganizationAdmin" to the identity pool. Add your personal user or the technical user (can be a Azure system-managed identity, too.) to that security group.

For interactive usage, just run "az login" in your terminal, then start the tool. If you run the tool directly on Azure, enable the system managed identity and add that identity to the abovementioned security group.

### Run the tool

If you run the tool from the command line, you need to configure your Python virtual environment properly. This example uses the `uv` package manager for Python. Enter the `src/confluent_cloud_service_quota_prometheus` folder. The run:

```console
uv sync
```

Then you can run the exporter:

```console
uv run python src/confluent_cloud_service_quota_prometheus/ccloud_prometheus_quota_api_exporter.py config.yaml
```

You can stop the tool simply by pressing Ctrl-C.
