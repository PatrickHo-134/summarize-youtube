Architecting a Custom Domain: Cloudflare + AWS CloudFront
=========================================================

Core Networking Concepts
------------------------

### SSL/TLS (Secure Sockets Layer / Transport Layer Security)

SSL and its modern successor, TLS, are cryptographic protocols designed to provide secure, encrypted communication over the internet.

-   **Encryption:** It scrambles the data transmitted between a user's browser and the web server, ensuring that intermediaries cannot read intercepted traffic.

-   **Authentication:** It uses digital certificates (issued by a Certificate Authority like AWS ACM) to cryptographically prove to the browser that the server it is communicating with is the legitimate owner of the domain.

### DNS Records (Domain Name System)

DNS is the internet's directory system. Computers communicate using IP addresses, but humans use readable domain names like `patrickho.dev`. DNS records are instructions hosted on DNS servers (like Cloudflare) that tell routing systems how to handle requests for a domain. Common types include:

-   **A Records:** Maps a domain directly to an IPv4 address.

-   **MX Records:** Routes email delivery for the domain.

-   **TXT Records:** Holds text information often used for domain verification and security policies.

### CNAME (Canonical Name) Record

A CNAME is a specific type of DNS record that maps an alias domain name to another canonical (primary) domain name, rather than to an IP address.

-   **How it works:** When a user visits `youtubesummary.patrickho.dev`, the DNS resolver looks up its CNAME record. If it points to `d1i*******.cloudfront.net`, the resolver then fetches the IP addresses for that CloudFront distribution and connects the user.

-   **Cloud Advantage:** CNAMEs are heavily used in AWS and cloud infrastructure because services like CloudFront use dynamic IP pools that change frequently. By pointing a CNAME to the underlying Amazon domain, traffic is always routed correctly regardless of the underlying IP changes.

Step-by-Step Deployment Guide for `youtubesummary.patrickho.dev`
----------------------------------------------------------------

### Step 1: Request the SSL/TLS Certificate in AWS ACM

To serve traffic securely over HTTPS, you must generate a public certificate.

1.  Log into the AWS Management Console and open **Certificate Manager (ACM)**.

2.  **Crucial Region Requirement:** Change the AWS region to **US East (N. Virginia) `us-east-1`** in the top navigation bar. AWS strictly requires that any certificate used with a global CloudFront distribution must be requested or imported into `us-east-1`. Certificates provisioned in local regions (like Sydney) will not be visible to CloudFront.

3.  Click **Request a certificate** > **Request a public certificate**.

4.  Enter the fully qualified domain name: `youtubesummary.patrickho.dev`.

5.  Select **DNS validation** and submit the request.

### Step 2: Validate Certificate Ownership via Cloudflare DNS

AWS needs proof that you control `patrickho.dev` before issuing the certificate.

1.  Open the pending certificate in AWS ACM and copy the provided **CNAME name** (e.g., `_42db********.youtubesummary.patrickho.dev.`) and **CNAME value** (e.g., `_6ee5e39a...acm-validations.aws.`).

2.  Log into the **Cloudflare Dashboard**, select the `patrickho.dev` domain, and navigate to **DNS > Records**.

3.  Create a new validation record:

    -   **Type:** `CNAME`

    -   **Name:** Paste the ACM CNAME name, but *remove* the root domain suffix so it just reads `_42db********.youtubesummary`. Cloudflare will append the rest automatically.

    -   **Target:** Paste the ACM CNAME value.

    -   **Proxy status:** Toggle to **DNS Only (Grey Cloud)**. AWS must be able to query this exact string natively without Cloudflare intervening with its proxy servers.

4.  Save the record. AWS will automatically query this record and switch the certificate status to **Issued** within a few minutes.

### Step 3: Attach Domain & Certificate to AWS CloudFront

With the certificate provisioned globally, configure the CDN to accept the custom domain.

1.  Open the **AWS CloudFront** console and edit the **General Settings** of your distribution.

2.  Under **Alternate domain name (CNAME)**, add `youtubesummary.patrickho.dev`.

3.  Under **Custom SSL certificate**, open the dropdown menu and select the newly issued ACM certificate.

4.  Save changes and wait for the CloudFront deployment status to update.

### Step 4: Route Web Traffic via Cloudflare DNS

Direct public web traffic for the subdomain to the CloudFront edge network.

1.  Return to **Cloudflare > DNS > Records** and add a second CNAME record.

2.  Configure the traffic routing:

    -   **Type:** `CNAME`

    -   **Name:** `youtubesummary`

    -   **Target:** Your unique CloudFront distribution URL (e.g., `d1ix******.cloudfront.net`).

    -   **Proxy status:** **Proxied (Orange Cloud)**. This routes incoming traffic through Cloudflare's web application firewall (WAF) and DDoS mitigation layers before it ever reaches AWS.

### Step 5: Enforce Strict SSL Encryption in Cloudflare

By default, Cloudflare may try to communicate with backend servers over unencrypted HTTP, which causes infinite redirect loops (`ERR_TOO_MANY_REDIRECTS`) if CloudFront enforces HTTPS.

1.  In Cloudflare, navigate to **SSL/TLS > Overview**.

2.  Set the encryption mode to **Full (strict)**. This guarantees end-to-end encryption by forcing Cloudflare to connect to CloudFront strictly over HTTPS, cryptographically validating the ACM certificate on the backend.