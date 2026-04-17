"""
Mock company data API — 50 realistic company records with a filter engine.
Used by RetrievalAgent in place of a real data provider (e.g. Explorium).
"""
from __future__ import annotations
import re
from typing import Any, Dict, List, Optional

from backend.models.schemas import (
    CompanyRecord, FundingStage, HiringVelocity, KeyContact, SizeBand
)


# ---------------------------------------------------------------------------
# Raw company dataset (50 entries)
# ---------------------------------------------------------------------------

_RAW_COMPANIES: List[Dict[str, Any]] = [
    {
        "id": "comp_001", "name": "Vanta", "domain": "vanta.com",
        "industry": "SaaS", "sub_industry": "Security & Compliance",
        "company_size": 400, "size_band": "mid-market", "geography": "US", "hq_city": "San Francisco",
        "funding_stage": "Series C", "total_funding_usd": 203_000_000, "last_funding_date": "2025-10-01",
        "revenue_range": "$50M-$100M", "tech_stack": ["AWS", "Python", "React", "PostgreSQL", "Terraform"],
        "hiring_roles": ["VP of Sales", "Senior Account Executive", "Security Engineer"],
        "hiring_velocity": "high", "growth_yoy": 1.2,
        "recent_news": "Raised $150M Series C to expand enterprise compliance platform",
        "description": "Automated security compliance platform for SOC 2, ISO 27001, HIPAA",
        "icp_tags": ["high-growth", "series-c", "security", "enterprise-expansion"],
        "competitors": ["Drata", "Secureframe", "Tugboat Logic"],
        "key_contacts": [{"name": "Christina Cacioppo", "title": "CEO"}, {"name": "James Vaughn", "title": "VP Sales"}]
    },
    {
        "id": "comp_002", "name": "Rippling", "domain": "rippling.com",
        "industry": "SaaS", "sub_industry": "HR & Workforce Management",
        "company_size": 2500, "size_band": "enterprise", "geography": "US", "hq_city": "San Francisco",
        "funding_stage": "Series F", "total_funding_usd": 1_200_000_000, "last_funding_date": "2024-04-12",
        "revenue_range": "$300M+", "tech_stack": ["AWS", "Python", "React", "MongoDB", "Kafka"],
        "hiring_roles": ["Enterprise Sales Director", "Customer Success Manager", "DevOps Engineer"],
        "hiring_velocity": "high", "growth_yoy": 0.75,
        "recent_news": "Expanding into EMEA market with new London office",
        "description": "All-in-one HR, IT, and Finance platform for fast-growing companies",
        "icp_tags": ["unicorn", "hr-tech", "enterprise", "global-expansion"],
        "competitors": ["Workday", "BambooHR", "Deel"],
        "key_contacts": [{"name": "Parker Conrad", "title": "CEO"}, {"name": "Matt Epstein", "title": "CMO"}]
    },
    {
        "id": "comp_003", "name": "Deel", "domain": "deel.com",
        "industry": "FinTech", "sub_industry": "Global Payroll & Compliance",
        "company_size": 3000, "size_band": "enterprise", "geography": "US", "hq_city": "San Francisco",
        "funding_stage": "Series D", "total_funding_usd": 679_000_000, "last_funding_date": "2023-05-15",
        "revenue_range": "$300M+", "tech_stack": ["GCP", "Node.js", "React", "PostgreSQL"],
        "hiring_roles": ["VP of Sales APAC", "Revenue Operations Manager", "Legal Counsel"],
        "hiring_velocity": "medium", "growth_yoy": 0.6,
        "recent_news": "Acquired Assemble to add compensation management",
        "description": "Global payroll and compliance platform for remote teams",
        "icp_tags": ["fintech", "global-payroll", "remote-work", "series-d"],
        "competitors": ["Remote.com", "Rippling", "Papaya Global"],
        "key_contacts": [{"name": "Alex Bouaziz", "title": "CEO"}, {"name": "Nadia Vatalidis", "title": "VP People"}]
    },
    {
        "id": "comp_004", "name": "Jasper", "domain": "jasper.ai",
        "industry": "AI SaaS", "sub_industry": "Content Generation",
        "company_size": 200, "size_band": "smb", "geography": "US", "hq_city": "Austin",
        "funding_stage": "Series A", "total_funding_usd": 131_000_000, "last_funding_date": "2022-10-18",
        "revenue_range": "$10M-$50M", "tech_stack": ["AWS", "Python", "OpenAI API", "React", "Stripe"],
        "hiring_roles": ["Head of Sales", "Product Marketing Manager", "ML Engineer"],
        "hiring_velocity": "medium", "growth_yoy": 0.4,
        "recent_news": "Launched Jasper for Business with team collaboration features",
        "description": "AI writing assistant for marketing teams and content creators",
        "icp_tags": ["ai-saas", "content-marketing", "series-a"],
        "competitors": ["Copy.ai", "Writer.com", "Grammarly"],
        "key_contacts": [{"name": "Dave Rogenmoser", "title": "CEO"}]
    },
    {
        "id": "comp_005", "name": "Gong", "domain": "gong.io",
        "industry": "AI SaaS", "sub_industry": "Revenue Intelligence",
        "company_size": 1500, "size_band": "enterprise", "geography": "US", "hq_city": "San Francisco",
        "funding_stage": "Series E", "total_funding_usd": 584_000_000, "last_funding_date": "2021-08-16",
        "revenue_range": "$100M-$300M", "tech_stack": ["AWS", "Python", "React", "Elasticsearch", "Snowflake"],
        "hiring_roles": ["Enterprise Account Executive", "Senior Sales Engineer", "Data Scientist"],
        "hiring_velocity": "medium", "growth_yoy": 0.45,
        "recent_news": "Launched Gong Engage for AI-powered sales engagement",
        "description": "Revenue intelligence platform using AI to analyze sales conversations",
        "icp_tags": ["ai-saas", "sales-tech", "enterprise", "revenue-intelligence"],
        "competitors": ["Chorus.ai", "Clari", "Outreach"],
        "key_contacts": [{"name": "Amit Bendov", "title": "CEO"}, {"name": "Eilon Reshef", "title": "CPO"}]
    },
    {
        "id": "comp_006", "name": "Pendo", "domain": "pendo.io",
        "industry": "SaaS", "sub_industry": "Product Analytics",
        "company_size": 800, "size_band": "mid-market", "geography": "US", "hq_city": "Raleigh",
        "funding_stage": "Series F", "total_funding_usd": 358_000_000, "last_funding_date": "2021-01-12",
        "revenue_range": "$100M-$300M", "tech_stack": ["AWS", "React", "Node.js", "MongoDB", "Segment"],
        "hiring_roles": ["VP of Enterprise Sales", "Customer Success Lead", "Data Engineer"],
        "hiring_velocity": "medium", "growth_yoy": 0.35,
        "recent_news": "Partnered with Salesforce AppExchange for deeper CRM integration",
        "description": "Product analytics and in-app guidance platform for SaaS companies",
        "icp_tags": ["product-analytics", "saas", "enterprise"],
        "competitors": ["Amplitude", "Mixpanel", "FullStory"],
        "key_contacts": [{"name": "Todd Olson", "title": "CEO"}]
    },
    {
        "id": "comp_007", "name": "Brex", "domain": "brex.com",
        "industry": "FinTech", "sub_industry": "Corporate Cards & Spend Management",
        "company_size": 1200, "size_band": "enterprise", "geography": "US", "hq_city": "San Francisco",
        "funding_stage": "Series D", "total_funding_usd": 1_500_000_000, "last_funding_date": "2022-01-11",
        "revenue_range": "$100M-$300M", "tech_stack": ["AWS", "Elixir", "React", "PostgreSQL", "Stripe"],
        "hiring_roles": ["VP Sales - Enterprise", "Finance Analyst", "Backend Engineer"],
        "hiring_velocity": "low", "growth_yoy": 0.3,
        "recent_news": "Shifted focus to enterprise clients after exiting SMB market",
        "description": "Corporate card and spend management for modern enterprises",
        "icp_tags": ["fintech", "spend-management", "enterprise", "series-d"],
        "competitors": ["Ramp", "Divvy", "Airbase"],
        "key_contacts": [{"name": "Pedro Franceschi", "title": "CEO"}, {"name": "Henrique Dubugras", "title": "Co-CEO"}]
    },
    {
        "id": "comp_008", "name": "Ramp", "domain": "ramp.com",
        "industry": "FinTech", "sub_industry": "Expense Management",
        "company_size": 900, "size_band": "mid-market", "geography": "US", "hq_city": "New York",
        "funding_stage": "Series C", "total_funding_usd": 750_000_000, "last_funding_date": "2026-01-20",
        "revenue_range": "$100M-$300M", "tech_stack": ["AWS", "Python", "React", "PostgreSQL", "dbt"],
        "hiring_roles": ["VP of Sales", "Account Executive - Mid Market", "ML Engineer"],
        "hiring_velocity": "high", "growth_yoy": 1.5,
        "recent_news": "Raised $150M to accelerate AI-powered finance automation",
        "description": "Finance automation platform that helps companies spend less",
        "icp_tags": ["high-growth", "fintech", "ai-finance", "series-c"],
        "competitors": ["Brex", "Divvy", "Expensify"],
        "key_contacts": [{"name": "Eric Glyman", "title": "CEO"}, {"name": "Genevieve Dombrowski", "title": "VP Sales"}]
    },
    {
        "id": "comp_009", "name": "Replit", "domain": "replit.com",
        "industry": "AI SaaS", "sub_industry": "Developer Tools",
        "company_size": 180, "size_band": "smb", "geography": "US", "hq_city": "San Francisco",
        "funding_stage": "Series B", "total_funding_usd": 222_000_000, "last_funding_date": "2023-04-25",
        "revenue_range": "$10M-$50M", "tech_stack": ["GCP", "Python", "React", "Nix", "WebAssembly"],
        "hiring_roles": ["Head of Enterprise Sales", "Developer Advocate", "AI Researcher"],
        "hiring_velocity": "medium", "growth_yoy": 0.9,
        "recent_news": "Launched Replit Agent for AI-assisted app development",
        "description": "Cloud-based IDE and collaborative coding platform with AI features",
        "icp_tags": ["ai-saas", "developer-tools", "series-b", "high-growth"],
        "competitors": ["GitHub Codespaces", "CodeSandbox", "Cursor"],
        "key_contacts": [{"name": "Amjad Masad", "title": "CEO"}]
    },
    {
        "id": "comp_010", "name": "Ironclad", "domain": "ironcladapp.com",
        "industry": "SaaS", "sub_industry": "Contract Lifecycle Management",
        "company_size": 350, "size_band": "mid-market", "geography": "US", "hq_city": "San Francisco",
        "funding_stage": "Series D", "total_funding_usd": 333_000_000, "last_funding_date": "2021-11-30",
        "revenue_range": "$50M-$100M", "tech_stack": ["AWS", "Java", "React", "PostgreSQL", "Salesforce"],
        "hiring_roles": ["Enterprise Sales Executive", "Customer Success Manager", "Implementation Specialist"],
        "hiring_velocity": "medium", "growth_yoy": 0.5,
        "recent_news": "Integrating AI contract analysis to reduce legal review time by 80%",
        "description": "Digital contract management platform for legal and procurement teams",
        "icp_tags": ["legaltech", "enterprise-saas", "series-d"],
        "competitors": ["DocuSign CLM", "Agiloft", "ContractPodAi"],
        "key_contacts": [{"name": "Jason Boehmig", "title": "CEO"}]
    },
    {
        "id": "comp_011", "name": "Hex Technologies", "domain": "hex.tech",
        "industry": "AI SaaS", "sub_industry": "Data Analytics",
        "company_size": 120, "size_band": "smb", "geography": "US", "hq_city": "San Francisco",
        "funding_stage": "Series B", "total_funding_usd": 52_000_000, "last_funding_date": "2025-09-10",
        "revenue_range": "$5M-$10M", "tech_stack": ["AWS", "Python", "React", "PostgreSQL", "dbt", "Snowflake"],
        "hiring_roles": ["VP of Sales", "Sales Development Rep", "Data Engineer"],
        "hiring_velocity": "high", "growth_yoy": 1.1,
        "recent_news": "Raised $30M Series B to build AI-native data workspace",
        "description": "Collaborative data workspace combining notebooks, apps, and AI",
        "icp_tags": ["ai-saas", "data-analytics", "series-b", "high-growth"],
        "competitors": ["Databricks", "Mode", "Observable"],
        "key_contacts": [{"name": "Barry McCardel", "title": "CEO"}]
    },
    {
        "id": "comp_012", "name": "Retool", "domain": "retool.com",
        "industry": "SaaS", "sub_industry": "Internal Tools",
        "company_size": 600, "size_band": "mid-market", "geography": "US", "hq_city": "San Francisco",
        "funding_stage": "Series C", "total_funding_usd": 445_000_000, "last_funding_date": "2022-03-09",
        "revenue_range": "$50M-$100M", "tech_stack": ["AWS", "TypeScript", "React", "PostgreSQL", "Docker"],
        "hiring_roles": ["Account Executive - Enterprise", "Solutions Engineer", "Product Manager"],
        "hiring_velocity": "medium", "growth_yoy": 0.55,
        "recent_news": "Launched Retool AI for building LLM-powered internal tools",
        "description": "Low-code platform for building internal business applications",
        "icp_tags": ["low-code", "developer-tools", "series-c"],
        "competitors": ["Appsmith", "Budibase", "Superblocks"],
        "key_contacts": [{"name": "David Hsu", "title": "CEO"}]
    },
    {
        "id": "comp_013", "name": "Fivetran", "domain": "fivetran.com",
        "industry": "SaaS", "sub_industry": "Data Integration",
        "company_size": 1400, "size_band": "enterprise", "geography": "US", "hq_city": "Oakland",
        "funding_stage": "Series D", "total_funding_usd": 563_000_000, "last_funding_date": "2021-09-14",
        "revenue_range": "$100M-$300M", "tech_stack": ["GCP", "Java", "Python", "Snowflake", "BigQuery"],
        "hiring_roles": ["Enterprise Account Executive", "Sales Engineering Manager", "Data Architect"],
        "hiring_velocity": "low", "growth_yoy": 0.3,
        "recent_news": "Expanded connector catalog to 500+ data sources",
        "description": "Automated data movement and transformation pipeline platform",
        "icp_tags": ["data-integration", "enterprise", "etl"],
        "competitors": ["Airbyte", "Stitch", "Matillion"],
        "key_contacts": [{"name": "George Fraser", "title": "CEO"}]
    },
    {
        "id": "comp_014", "name": "Persona", "domain": "withpersona.com",
        "industry": "SaaS", "sub_industry": "Identity Verification",
        "company_size": 250, "size_band": "mid-market", "geography": "US", "hq_city": "San Francisco",
        "funding_stage": "Series C", "total_funding_usd": 220_000_000, "last_funding_date": "2022-11-08",
        "revenue_range": "$10M-$50M", "tech_stack": ["AWS", "Ruby on Rails", "React", "PostgreSQL"],
        "hiring_roles": ["VP Sales", "Senior Sales Engineer", "Compliance Engineer"],
        "hiring_velocity": "medium", "growth_yoy": 0.65,
        "recent_news": "Launched AI-powered fraud detection suite for fintech companies",
        "description": "Identity verification and KYC compliance platform",
        "icp_tags": ["identity-verification", "fintech-infra", "series-c"],
        "competitors": ["Jumio", "Onfido", "Stripe Identity"],
        "key_contacts": [{"name": "Rick Song", "title": "CEO"}]
    },
    {
        "id": "comp_015", "name": "Clerk", "domain": "clerk.com",
        "industry": "SaaS", "sub_industry": "Authentication & Identity",
        "company_size": 80, "size_band": "startup", "geography": "US", "hq_city": "New York",
        "funding_stage": "Series B", "total_funding_usd": 57_000_000, "last_funding_date": "2026-02-14",
        "revenue_range": "$5M-$10M", "tech_stack": ["AWS", "TypeScript", "React", "PostgreSQL", "Redis"],
        "hiring_roles": ["Head of Sales", "Developer Advocate", "Solutions Architect"],
        "hiring_velocity": "high", "growth_yoy": 2.1,
        "recent_news": "Raised $30M Series B as developer authentication demand surges",
        "description": "Complete authentication and user management for developers",
        "icp_tags": ["developer-tools", "auth", "series-b", "high-growth"],
        "competitors": ["Auth0", "Firebase Auth", "Supabase Auth"],
        "key_contacts": [{"name": "Colin Sidoti", "title": "CEO"}]
    },
    {
        "id": "comp_016", "name": "Drata", "domain": "drata.com",
        "industry": "SaaS", "sub_industry": "Security & Compliance Automation",
        "company_size": 500, "size_band": "mid-market", "geography": "US", "hq_city": "San Diego",
        "funding_stage": "Series C", "total_funding_usd": 328_000_000, "last_funding_date": "2022-12-01",
        "revenue_range": "$50M-$100M", "tech_stack": ["AWS", "Node.js", "React", "PostgreSQL", "Terraform"],
        "hiring_roles": ["Enterprise Account Executive", "VP Sales", "Trust & Safety Lead"],
        "hiring_velocity": "high", "growth_yoy": 1.3,
        "recent_news": "Reached 3,000 customers and $100M ARR milestone",
        "description": "Continuous compliance automation platform for SOC 2 and ISO 27001",
        "icp_tags": ["high-growth", "compliance", "series-c", "enterprise-expansion"],
        "competitors": ["Vanta", "Secureframe", "Tugboat Logic"],
        "key_contacts": [{"name": "Adam Markowitz", "title": "CEO"}]
    },
    {
        "id": "comp_017", "name": "Airtable", "domain": "airtable.com",
        "industry": "SaaS", "sub_industry": "No-Code Database",
        "company_size": 1800, "size_band": "enterprise", "geography": "US", "hq_city": "San Francisco",
        "funding_stage": "Series F", "total_funding_usd": 1_360_000_000, "last_funding_date": "2021-12-15",
        "revenue_range": "$100M-$300M", "tech_stack": ["AWS", "Node.js", "React", "MySQL", "Redis"],
        "hiring_roles": ["Senior Account Executive", "Sales Operations Manager", "Full-Stack Engineer"],
        "hiring_velocity": "low", "growth_yoy": 0.2,
        "recent_news": "Restructuring team to focus on enterprise AI features",
        "description": "Flexible no-code platform combining spreadsheets with databases",
        "icp_tags": ["no-code", "collaboration", "enterprise"],
        "competitors": ["Notion", "Monday.com", "Smartsheet"],
        "key_contacts": [{"name": "Howie Liu", "title": "CEO"}]
    },
    {
        "id": "comp_018", "name": "Hightouch", "domain": "hightouch.com",
        "industry": "SaaS", "sub_industry": "Reverse ETL & Data Activation",
        "company_size": 110, "size_band": "startup", "geography": "US", "hq_city": "San Francisco",
        "funding_stage": "Series B", "total_funding_usd": 38_000_000, "last_funding_date": "2025-11-20",
        "revenue_range": "$5M-$10M", "tech_stack": ["AWS", "Python", "TypeScript", "Snowflake", "dbt", "BigQuery"],
        "hiring_roles": ["VP of Sales", "Account Executive", "Data Engineer"],
        "hiring_velocity": "high", "growth_yoy": 1.4,
        "recent_news": "Raised $38M Series B to expand AI-powered marketing data activation",
        "description": "Data activation platform syncing warehouse data to business tools",
        "icp_tags": ["data-activation", "reverse-etl", "series-b", "high-growth"],
        "competitors": ["Census", "Polytomic", "Rudderstack"],
        "key_contacts": [{"name": "Tejas Manohar", "title": "CEO"}]
    },
    {
        "id": "comp_019", "name": "Loom", "domain": "loom.com",
        "industry": "SaaS", "sub_industry": "Video Messaging",
        "company_size": 400, "size_band": "mid-market", "geography": "US", "hq_city": "San Francisco",
        "funding_stage": "Series C", "total_funding_usd": 203_000_000, "last_funding_date": "2021-05-25",
        "revenue_range": "$50M-$100M", "tech_stack": ["AWS", "React", "Node.js", "WebRTC", "PostgreSQL"],
        "hiring_roles": ["Sales Manager", "Customer Success", "Video AI Engineer"],
        "hiring_velocity": "low", "growth_yoy": 0.15,
        "recent_news": "Acquired by Atlassian for $975M to integrate into productivity suite",
        "description": "Async video messaging platform for workplace communication",
        "icp_tags": ["productivity", "video-communication", "acquired"],
        "competitors": ["Vidyard", "Wistia", "Screencastify"],
        "key_contacts": [{"name": "Joe Thomas", "title": "CEO"}]
    },
    {
        "id": "comp_020", "name": "Linear", "domain": "linear.app",
        "industry": "SaaS", "sub_industry": "Project Management",
        "company_size": 60, "size_band": "startup", "geography": "US", "hq_city": "San Francisco",
        "funding_stage": "Series B", "total_funding_usd": 52_000_000, "last_funding_date": "2022-07-19",
        "revenue_range": "$5M-$10M", "tech_stack": ["AWS", "TypeScript", "React", "PostgreSQL", "GraphQL"],
        "hiring_roles": ["Head of Sales", "Product Engineer", "Designer"],
        "hiring_velocity": "low", "growth_yoy": 0.55,
        "recent_news": "Reached 10,000 paying teams milestone",
        "description": "Issue tracking and project management tool for software teams",
        "icp_tags": ["developer-tools", "project-management", "series-b"],
        "competitors": ["Jira", "GitHub Issues", "Shortcut"],
        "key_contacts": [{"name": "Karri Saarinen", "title": "CEO"}]
    },
    {
        "id": "comp_021", "name": "Vercel", "domain": "vercel.com",
        "industry": "SaaS", "sub_industry": "Cloud Deployment",
        "company_size": 700, "size_band": "mid-market", "geography": "US", "hq_city": "San Francisco",
        "funding_stage": "Series E", "total_funding_usd": 563_000_000, "last_funding_date": "2024-05-23",
        "revenue_range": "$100M-$300M", "tech_stack": ["AWS", "TypeScript", "Next.js", "Edge", "PostgreSQL"],
        "hiring_roles": ["Enterprise Sales Lead", "Solutions Engineer", "Infrastructure Engineer"],
        "hiring_velocity": "medium", "growth_yoy": 0.7,
        "recent_news": "Launched V0 AI web builder and raised $250M Series E",
        "description": "Frontend cloud platform for deploying web applications",
        "icp_tags": ["developer-tools", "cloud-infra", "series-e", "ai-product"],
        "competitors": ["Netlify", "AWS Amplify", "Cloudflare Pages"],
        "key_contacts": [{"name": "Guillermo Rauch", "title": "CEO"}]
    },
    {
        "id": "comp_022", "name": "Descript", "domain": "descript.com",
        "industry": "AI SaaS", "sub_industry": "Audio/Video Editing",
        "company_size": 150, "size_band": "smb", "geography": "US", "hq_city": "San Francisco",
        "funding_stage": "Series C", "total_funding_usd": 100_000_000, "last_funding_date": "2023-09-14",
        "revenue_range": "$10M-$50M", "tech_stack": ["AWS", "Python", "React", "WebRTC", "ML"],
        "hiring_roles": ["Head of Revenue", "Sales Development Rep", "AI/ML Engineer"],
        "hiring_velocity": "medium", "growth_yoy": 0.65,
        "recent_news": "Launched AI podcast production suite with auto-publishing",
        "description": "AI-powered video and podcast editing platform for creators",
        "icp_tags": ["ai-saas", "content-creation", "series-c"],
        "competitors": ["Adobe Premiere", "Riverside.fm", "Transistor"],
        "key_contacts": [{"name": "Andrew Mason", "title": "CEO"}]
    },
    {
        "id": "comp_023", "name": "Ashby", "domain": "ashbyhq.com",
        "industry": "SaaS", "sub_industry": "Recruiting & ATS",
        "company_size": 90, "size_band": "startup", "geography": "US", "hq_city": "San Francisco",
        "funding_stage": "Series B", "total_funding_usd": 56_000_000, "last_funding_date": "2025-08-05",
        "revenue_range": "$5M-$10M", "tech_stack": ["AWS", "TypeScript", "React", "PostgreSQL"],
        "hiring_roles": ["VP Sales", "Account Executive - Mid Market", "Software Engineer"],
        "hiring_velocity": "high", "growth_yoy": 1.8,
        "recent_news": "Raised $29M to bring AI recruiting analytics to mid-market companies",
        "description": "All-in-one recruiting software with advanced analytics and AI",
        "icp_tags": ["hr-tech", "recruiting", "series-b", "high-growth"],
        "competitors": ["Lever", "Greenhouse", "Workable"],
        "key_contacts": [{"name": "Benji Encz", "title": "CEO"}]
    },
    {
        "id": "comp_024", "name": "Findem", "domain": "findem.ai",
        "industry": "AI SaaS", "sub_industry": "Talent Intelligence",
        "company_size": 130, "size_band": "smb", "geography": "US", "hq_city": "Redwood City",
        "funding_stage": "Series B", "total_funding_usd": 47_000_000, "last_funding_date": "2022-11-01",
        "revenue_range": "$5M-$10M", "tech_stack": ["AWS", "Python", "React", "Elasticsearch", "ML"],
        "hiring_roles": ["VP Sales", "Customer Success Lead", "Data Scientist"],
        "hiring_velocity": "medium", "growth_yoy": 0.6,
        "recent_news": "Launched AI-powered talent market intelligence product",
        "description": "AI-powered talent sourcing and people data platform",
        "icp_tags": ["ai-saas", "hr-tech", "talent-intelligence", "series-b"],
        "competitors": ["SeekOut", "Eightfold.ai", "LinkedIn Recruiter"],
        "key_contacts": [{"name": "Hari Kolam", "title": "CEO"}]
    },
    {
        "id": "comp_025", "name": "Synthesia", "domain": "synthesia.io",
        "industry": "AI SaaS", "sub_industry": "AI Video Generation",
        "company_size": 300, "size_band": "mid-market", "geography": "UK", "hq_city": "London",
        "funding_stage": "Series C", "total_funding_usd": 157_000_000, "last_funding_date": "2023-06-19",
        "revenue_range": "$50M-$100M", "tech_stack": ["GCP", "Python", "React", "TensorFlow", "PyTorch"],
        "hiring_roles": ["VP Sales Americas", "Enterprise Account Executive", "AI Researcher"],
        "hiring_velocity": "high", "growth_yoy": 1.0,
        "recent_news": "Expanding US sales team after tripling enterprise customer base",
        "description": "AI video generation platform for enterprise training and communications",
        "icp_tags": ["ai-saas", "video-generation", "series-c", "enterprise-expansion"],
        "competitors": ["HeyGen", "D-ID", "Runway"],
        "key_contacts": [{"name": "Victor Riparbelli", "title": "CEO"}]
    },
    {
        "id": "comp_026", "name": "Cohere", "domain": "cohere.com",
        "industry": "AI SaaS", "sub_industry": "Enterprise AI / NLP",
        "company_size": 400, "size_band": "mid-market", "geography": "Canada", "hq_city": "Toronto",
        "funding_stage": "Series C", "total_funding_usd": 445_000_000, "last_funding_date": "2024-07-22",
        "revenue_range": "$50M-$100M", "tech_stack": ["GCP", "Python", "PyTorch", "Kubernetes", "CUDA"],
        "hiring_roles": ["VP Sales - Enterprise", "Solutions Architect", "ML Research Engineer"],
        "hiring_velocity": "high", "growth_yoy": 1.6,
        "recent_news": "Raised $500M to compete in enterprise AI with Command R+",
        "description": "Enterprise AI platform for NLP, embeddings, and RAG at scale",
        "icp_tags": ["ai-saas", "enterprise-ai", "nlp", "series-c", "high-growth"],
        "competitors": ["OpenAI API", "Anthropic", "Google Vertex AI"],
        "key_contacts": [{"name": "Aidan Gomez", "title": "CEO"}]
    },
    {
        "id": "comp_027", "name": "Productboard", "domain": "productboard.com",
        "industry": "SaaS", "sub_industry": "Product Management",
        "company_size": 450, "size_band": "mid-market", "geography": "US", "hq_city": "San Francisco",
        "funding_stage": "Series D", "total_funding_usd": 261_000_000, "last_funding_date": "2022-01-12",
        "revenue_range": "$50M-$100M", "tech_stack": ["AWS", "React", "Ruby on Rails", "PostgreSQL"],
        "hiring_roles": ["Enterprise Sales Executive", "Customer Success Manager", "Growth PM"],
        "hiring_velocity": "medium", "growth_yoy": 0.4,
        "recent_news": "Integrating AI features for automated customer feedback analysis",
        "description": "Product management platform for roadmapping and customer insights",
        "icp_tags": ["product-management", "enterprise", "series-d"],
        "competitors": ["Aha!", "Amplitude", "Coda"],
        "key_contacts": [{"name": "Hubert Palan", "title": "CEO"}]
    },
    {
        "id": "comp_028", "name": "Leapsome", "domain": "leapsome.com",
        "industry": "SaaS", "sub_industry": "HR Performance Management",
        "company_size": 200, "size_band": "smb", "geography": "Germany", "hq_city": "Berlin",
        "funding_stage": "Series A", "total_funding_usd": 60_000_000, "last_funding_date": "2022-02-28",
        "revenue_range": "$10M-$50M", "tech_stack": ["AWS", "TypeScript", "React", "PostgreSQL"],
        "hiring_roles": ["Sales Development Rep", "AE - DACH", "Product Engineer"],
        "hiring_velocity": "medium", "growth_yoy": 0.5,
        "recent_news": "Expanded to US market with new New York office",
        "description": "People management platform for performance reviews and OKRs",
        "icp_tags": ["hr-tech", "performance-management", "series-a", "emea"],
        "competitors": ["Lattice", "Culture Amp", "15Five"],
        "key_contacts": [{"name": "Jenny von Podewils", "title": "CEO"}]
    },
    {
        "id": "comp_029", "name": "Liveblocks", "domain": "liveblocks.io",
        "industry": "SaaS", "sub_industry": "Real-time Collaboration Infrastructure",
        "company_size": 30, "size_band": "startup", "geography": "UK", "hq_city": "London",
        "funding_stage": "Series A", "total_funding_usd": 20_000_000, "last_funding_date": "2022-12-06",
        "revenue_range": "$1M-$5M", "tech_stack": ["AWS", "TypeScript", "React", "WebSockets", "CRDTs"],
        "hiring_roles": ["Head of Business Development", "Developer Relations", "Backend Engineer"],
        "hiring_velocity": "low", "growth_yoy": 0.8,
        "recent_news": "Surpassed 2M developers using collaboration APIs",
        "description": "Real-time collaboration infrastructure APIs for product teams",
        "icp_tags": ["developer-tools", "collaboration-infra", "series-a"],
        "competitors": ["Yjs", "Automerge", "PartyKit"],
        "key_contacts": [{"name": "Steven Fabre", "title": "CEO"}]
    },
    {
        "id": "comp_030", "name": "Temporal", "domain": "temporal.io",
        "industry": "SaaS", "sub_industry": "Workflow Orchestration",
        "company_size": 250, "size_band": "mid-market", "geography": "US", "hq_city": "Seattle",
        "funding_stage": "Series B", "total_funding_usd": 103_000_000, "last_funding_date": "2022-02-17",
        "revenue_range": "$10M-$50M", "tech_stack": ["GCP", "Go", "Java", "Python", "Kubernetes"],
        "hiring_roles": ["Enterprise Account Executive", "VP Revenue", "Platform Engineer"],
        "hiring_velocity": "medium", "growth_yoy": 0.75,
        "recent_news": "Major adoption by Fortune 500 companies for mission-critical workflows",
        "description": "Open-source workflow orchestration engine for reliable distributed apps",
        "icp_tags": ["developer-tools", "workflow-orchestration", "series-b"],
        "competitors": ["Airflow", "Conductor", "AWS Step Functions"],
        "key_contacts": [{"name": "Maxim Fateev", "title": "CEO"}]
    },
    {
        "id": "comp_031", "name": "Speakeasy", "domain": "speakeasyapi.dev",
        "industry": "SaaS", "sub_industry": "API Developer Experience",
        "company_size": 25, "size_band": "startup", "geography": "US", "hq_city": "San Francisco",
        "funding_stage": "Seed", "total_funding_usd": 11_000_000, "last_funding_date": "2023-03-14",
        "revenue_range": "$1M-$5M", "tech_stack": ["AWS", "Go", "TypeScript", "OpenAPI"],
        "hiring_roles": ["Business Development", "Developer Advocate", "Go Engineer"],
        "hiring_velocity": "low", "growth_yoy": 1.2,
        "recent_news": "Launched SDK generation from OpenAPI specs for 10 languages",
        "description": "API tooling platform that auto-generates SDKs and documentation",
        "icp_tags": ["developer-tools", "api-tooling", "seed"],
        "competitors": ["Stainless", "Fern", "Kiota"],
        "key_contacts": [{"name": "Nolan Sullivan", "title": "CEO"}]
    },
    {
        "id": "comp_032", "name": "Merge", "domain": "merge.dev",
        "industry": "SaaS", "sub_industry": "Unified API Integration",
        "company_size": 100, "size_band": "smb", "geography": "US", "hq_city": "New York",
        "funding_stage": "Series B", "total_funding_usd": 55_000_000, "last_funding_date": "2022-05-11",
        "revenue_range": "$5M-$10M", "tech_stack": ["AWS", "Python", "React", "PostgreSQL"],
        "hiring_roles": ["VP Sales", "Solutions Engineer", "Integrations Engineer"],
        "hiring_velocity": "medium", "growth_yoy": 0.9,
        "recent_news": "Expanded unified API to cover 200+ HR and payroll integrations",
        "description": "Unified API platform for embedding HRIS, ATS, and payroll integrations",
        "icp_tags": ["developer-tools", "api-integrations", "series-b"],
        "competitors": ["Finch", "Knit", "Apideck"],
        "key_contacts": [{"name": "Shensi Ding", "title": "CEO"}]
    },
    {
        "id": "comp_033", "name": "Airbyte", "domain": "airbyte.com",
        "industry": "SaaS", "sub_industry": "Open Source Data Integration",
        "company_size": 350, "size_band": "mid-market", "geography": "US", "hq_city": "San Francisco",
        "funding_stage": "Series B", "total_funding_usd": 181_000_000, "last_funding_date": "2022-12-13",
        "revenue_range": "$10M-$50M", "tech_stack": ["GCP", "Python", "Java", "Kubernetes", "dbt"],
        "hiring_roles": ["Enterprise Sales Lead", "DevRel", "Data Platform Engineer"],
        "hiring_velocity": "medium", "growth_yoy": 0.7,
        "recent_news": "Reached 40,000 community deployments and launched cloud offering",
        "description": "Open source ELT data integration platform with 350+ connectors",
        "icp_tags": ["open-source", "data-integration", "series-b"],
        "competitors": ["Fivetran", "Stitch", "Matillion"],
        "key_contacts": [{"name": "Michel Tricot", "title": "CEO"}]
    },
    {
        "id": "comp_034", "name": "Runway", "domain": "runwayml.com",
        "industry": "AI SaaS", "sub_industry": "Generative AI / Video",
        "company_size": 200, "size_band": "smb", "geography": "US", "hq_city": "New York",
        "funding_stage": "Series C", "total_funding_usd": 236_000_000, "last_funding_date": "2024-08-12",
        "revenue_range": "$10M-$50M", "tech_stack": ["AWS", "Python", "PyTorch", "React", "CUDA"],
        "hiring_roles": ["Head of Revenue", "Enterprise Sales", "AI Research Scientist"],
        "hiring_velocity": "high", "growth_yoy": 1.9,
        "recent_news": "Gen-3 Alpha model used by major Hollywood studios",
        "description": "AI research company building tools for human creativity in film and media",
        "icp_tags": ["ai-saas", "generative-ai", "series-c", "high-growth"],
        "competitors": ["Pika", "Sora", "Stable Video Diffusion"],
        "key_contacts": [{"name": "Cristobal Valenzuela", "title": "CEO"}]
    },
    {
        "id": "comp_035", "name": "Glean", "domain": "glean.com",
        "industry": "AI SaaS", "sub_industry": "Enterprise Search",
        "company_size": 450, "size_band": "mid-market", "geography": "US", "hq_city": "Palo Alto",
        "funding_stage": "Series D", "total_funding_usd": 360_000_000, "last_funding_date": "2024-02-27",
        "revenue_range": "$50M-$100M", "tech_stack": ["GCP", "Python", "React", "Elasticsearch", "LLM"],
        "hiring_roles": ["VP Sales", "Enterprise Account Executive", "AI Platform Engineer"],
        "hiring_velocity": "high", "growth_yoy": 1.7,
        "recent_news": "Raised $200M Series D as enterprise AI search demand explodes",
        "description": "AI-powered workplace search and knowledge management platform",
        "icp_tags": ["ai-saas", "enterprise-search", "series-d", "high-growth"],
        "competitors": ["Microsoft Copilot", "Notion AI", "Guru"],
        "key_contacts": [{"name": "Arvind Jain", "title": "CEO"}]
    },
    {
        "id": "comp_036", "name": "Workato", "domain": "workato.com",
        "industry": "SaaS", "sub_industry": "iPaaS / Workflow Automation",
        "company_size": 900, "size_band": "mid-market", "geography": "US", "hq_city": "Mountain View",
        "funding_stage": "Series E", "total_funding_usd": 405_000_000, "last_funding_date": "2021-12-08",
        "revenue_range": "$100M-$300M", "tech_stack": ["AWS", "Ruby", "React", "PostgreSQL", "Kubernetes"],
        "hiring_roles": ["Enterprise Sales Executive", "Solutions Architect", "Partner Manager"],
        "hiring_velocity": "medium", "growth_yoy": 0.4,
        "recent_news": "Expanding partner ecosystem with 200+ technology partners",
        "description": "Intelligent automation platform connecting apps and automating workflows",
        "icp_tags": ["ipaas", "automation", "enterprise", "series-e"],
        "competitors": ["MuleSoft", "Zapier", "Boomi"],
        "key_contacts": [{"name": "Vijay Tella", "title": "CEO"}]
    },
    {
        "id": "comp_037", "name": "Torc", "domain": "torc.dev",
        "industry": "SaaS", "sub_industry": "Talent Marketplace",
        "company_size": 70, "size_band": "startup", "geography": "US", "hq_city": "Blacksburg",
        "funding_stage": "Series A", "total_funding_usd": 23_000_000, "last_funding_date": "2021-07-19",
        "revenue_range": "$1M-$5M", "tech_stack": ["AWS", "React", "Node.js", "PostgreSQL"],
        "hiring_roles": ["Head of Sales", "Community Manager", "Full-Stack Engineer"],
        "hiring_velocity": "low", "growth_yoy": 0.3,
        "recent_news": "Partnered with IBM to source AI-skilled developers",
        "description": "Developer talent marketplace connecting engineers with tech companies",
        "icp_tags": ["hr-tech", "talent-marketplace", "series-a"],
        "competitors": ["Toptal", "Turing.com", "Arc.dev"],
        "key_contacts": [{"name": "Michael Morris", "title": "CEO"}]
    },
    {
        "id": "comp_038", "name": "Dovetail", "domain": "dovetailapp.com",
        "industry": "SaaS", "sub_industry": "User Research",
        "company_size": 120, "size_band": "smb", "geography": "Australia", "hq_city": "Sydney",
        "funding_stage": "Series A", "total_funding_usd": 80_000_000, "last_funding_date": "2022-03-30",
        "revenue_range": "$10M-$50M", "tech_stack": ["AWS", "TypeScript", "React", "PostgreSQL"],
        "hiring_roles": ["Head of Sales", "Customer Research Specialist", "Product Engineer"],
        "hiring_velocity": "low", "growth_yoy": 0.45,
        "recent_news": "Launched AI tagging and sentiment analysis for research data",
        "description": "User research repository and analysis platform for product teams",
        "icp_tags": ["ux-research", "product-analytics", "series-a"],
        "competitors": ["Aurelius", "EnjoyHQ", "Maze"],
        "key_contacts": [{"name": "Benjamin Humphrey", "title": "CEO"}]
    },
    {
        "id": "comp_039", "name": "Prefect", "domain": "prefect.io",
        "industry": "SaaS", "sub_industry": "Data Orchestration",
        "company_size": 90, "size_band": "startup", "geography": "US", "hq_city": "Washington DC",
        "funding_stage": "Series B", "total_funding_usd": 32_000_000, "last_funding_date": "2021-10-19",
        "revenue_range": "$5M-$10M", "tech_stack": ["AWS", "Python", "React", "Kubernetes", "Prefect"],
        "hiring_roles": ["VP Revenue", "Enterprise Account Executive", "Developer Advocate"],
        "hiring_velocity": "medium", "growth_yoy": 0.6,
        "recent_news": "Prefect 3.0 launched with enhanced AI workflow support",
        "description": "Modern workflow orchestration for data and ML pipelines",
        "icp_tags": ["data-engineering", "orchestration", "series-b"],
        "competitors": ["Apache Airflow", "Dagster", "Luigi"],
        "key_contacts": [{"name": "Jeremiah Lowin", "title": "CEO"}]
    },
    {
        "id": "comp_040", "name": "Forter", "domain": "forter.com",
        "industry": "FinTech", "sub_industry": "Fraud Prevention",
        "company_size": 600, "size_band": "mid-market", "geography": "US", "hq_city": "New York",
        "funding_stage": "Series F", "total_funding_usd": 525_000_000, "last_funding_date": "2021-04-21",
        "revenue_range": "$100M-$300M", "tech_stack": ["AWS", "Python", "Scala", "Kafka", "Cassandra"],
        "hiring_roles": ["Enterprise Sales Executive", "Sales Engineer", "Data Scientist"],
        "hiring_velocity": "medium", "growth_yoy": 0.35,
        "recent_news": "Processing $200B in commerce transactions annually",
        "description": "AI-powered fraud prevention and trust platform for e-commerce",
        "icp_tags": ["fintech", "fraud-prevention", "enterprise", "series-f"],
        "competitors": ["Signifyd", "Riskified", "Kount"],
        "key_contacts": [{"name": "Michael Reitblat", "title": "CEO"}]
    },
    {
        "id": "comp_041", "name": "Livekit", "domain": "livekit.io",
        "industry": "SaaS", "sub_industry": "Real-time Audio/Video Infrastructure",
        "company_size": 40, "size_band": "startup", "geography": "US", "hq_city": "San Francisco",
        "funding_stage": "Series A", "total_funding_usd": 20_000_000, "last_funding_date": "2023-01-18",
        "revenue_range": "$1M-$5M", "tech_stack": ["AWS", "Go", "WebRTC", "TypeScript", "Kubernetes"],
        "hiring_roles": ["Head of Sales", "Developer Relations Engineer", "Platform Engineer"],
        "hiring_velocity": "medium", "growth_yoy": 1.3,
        "recent_news": "AI voice agents powered by LiveKit used by 500+ companies",
        "description": "Open source real-time audio/video infrastructure for AI voice agents",
        "icp_tags": ["developer-tools", "webrtc", "ai-voice", "series-a"],
        "competitors": ["Agora", "Daily.co", "Vonage"],
        "key_contacts": [{"name": "Russ d'Sa", "title": "CEO"}]
    },
    {
        "id": "comp_042", "name": "Incident.io", "domain": "incident.io",
        "industry": "SaaS", "sub_industry": "Incident Management",
        "company_size": 80, "size_band": "startup", "geography": "UK", "hq_city": "London",
        "funding_stage": "Series B", "total_funding_usd": 62_000_000, "last_funding_date": "2026-01-09",
        "revenue_range": "$5M-$10M", "tech_stack": ["GCP", "Go", "React", "PostgreSQL", "PagerDuty"],
        "hiring_roles": ["VP Sales", "Sales Development Rep", "Platform Engineer"],
        "hiring_velocity": "high", "growth_yoy": 1.5,
        "recent_news": "Raised $62M Series B to become the incident management standard",
        "description": "Modern incident management and on-call platform for engineering teams",
        "icp_tags": ["devops", "incident-management", "series-b", "high-growth"],
        "competitors": ["PagerDuty", "Opsgenie", "FireHydrant"],
        "key_contacts": [{"name": "Stephen Whitworth", "title": "CEO"}]
    },
    {
        "id": "comp_043", "name": "Stytch", "domain": "stytch.com",
        "industry": "SaaS", "sub_industry": "Authentication Infrastructure",
        "company_size": 60, "size_band": "startup", "geography": "US", "hq_city": "San Francisco",
        "funding_stage": "Series B", "total_funding_usd": 90_000_000, "last_funding_date": "2022-01-12",
        "revenue_range": "$5M-$10M", "tech_stack": ["AWS", "Go", "React", "PostgreSQL", "Redis"],
        "hiring_roles": ["Sales Engineer", "Head of Enterprise Sales", "Backend Engineer"],
        "hiring_velocity": "low", "growth_yoy": 0.5,
        "recent_news": "Expanded B2B SaaS auth product with org/team management APIs",
        "description": "Developer-first authentication platform with fraud signals",
        "icp_tags": ["developer-tools", "auth", "series-b"],
        "competitors": ["Auth0", "Clerk", "WorkOS"],
        "key_contacts": [{"name": "Reed McGinley-Stempel", "title": "CEO"}]
    },
    {
        "id": "comp_044", "name": "Orb", "domain": "withorb.com",
        "industry": "SaaS", "sub_industry": "Usage-Based Billing",
        "company_size": 45, "size_band": "startup", "geography": "US", "hq_city": "San Francisco",
        "funding_stage": "Series A", "total_funding_usd": 19_000_000, "last_funding_date": "2022-06-21",
        "revenue_range": "$1M-$5M", "tech_stack": ["AWS", "TypeScript", "React", "PostgreSQL", "Stripe"],
        "hiring_roles": ["VP Sales", "Sales Engineer", "Backend Engineer"],
        "hiring_velocity": "medium", "growth_yoy": 1.0,
        "recent_news": "Major AI API companies choosing Orb for usage-based billing",
        "description": "Billing infrastructure for usage-based and subscription pricing models",
        "icp_tags": ["fintech-infra", "billing", "series-a", "developer-tools"],
        "competitors": ["Zuora", "Chargebee", "Stripe Billing"],
        "key_contacts": [{"name": "Alvaro Morales", "title": "CEO"}]
    },
    {
        "id": "comp_045", "name": "Watershed", "domain": "watershedclimate.com",
        "industry": "SaaS", "sub_industry": "Climate Tech / ESG",
        "company_size": 180, "size_band": "smb", "geography": "US", "hq_city": "San Francisco",
        "funding_stage": "Series B", "total_funding_usd": 100_000_000, "last_funding_date": "2023-02-28",
        "revenue_range": "$10M-$50M", "tech_stack": ["AWS", "Python", "React", "PostgreSQL", "dbt"],
        "hiring_roles": ["Enterprise Sales Lead", "Climate Data Scientist", "Solutions Engineer"],
        "hiring_velocity": "medium", "growth_yoy": 0.8,
        "recent_news": "Signed Fortune 500 CPG companies for Scope 3 emissions tracking",
        "description": "Enterprise carbon management and net-zero strategy platform",
        "icp_tags": ["climate-tech", "esg", "enterprise", "series-b"],
        "competitors": ["Persefoni", "Greenly", "Salesforce Net Zero Cloud"],
        "key_contacts": [{"name": "Taylor Francis", "title": "CEO"}]
    },
    {
        "id": "comp_046", "name": "Twelve Labs", "domain": "twelvelabs.io",
        "industry": "AI SaaS", "sub_industry": "Video Understanding AI",
        "company_size": 55, "size_band": "startup", "geography": "US", "hq_city": "San Francisco",
        "funding_stage": "Series A", "total_funding_usd": 27_000_000, "last_funding_date": "2023-06-27",
        "revenue_range": "$1M-$5M", "tech_stack": ["AWS", "Python", "PyTorch", "React", "CUDA"],
        "hiring_roles": ["Head of Sales", "ML Researcher", "DevRel Engineer"],
        "hiring_velocity": "medium", "growth_yoy": 1.5,
        "recent_news": "Launched Marengo 2.6 for state-of-the-art video search",
        "description": "Multimodal video understanding AI for search and generation",
        "icp_tags": ["ai-saas", "video-ai", "series-a", "developer-tools"],
        "competitors": ["Google Video AI", "Amazon Rekognition", "Cloudinary"],
        "key_contacts": [{"name": "Jae Lee", "title": "CEO"}]
    },
    {
        "id": "comp_047", "name": "Rilla Voice", "domain": "rilla.com",
        "industry": "AI SaaS", "sub_industry": "Field Sales Intelligence",
        "company_size": 65, "size_band": "startup", "geography": "US", "hq_city": "New York",
        "funding_stage": "Series A", "total_funding_usd": 10_000_000, "last_funding_date": "2025-12-01",
        "revenue_range": "$5M-$10M", "tech_stack": ["AWS", "Python", "React", "AI/ML", "Whisper"],
        "hiring_roles": ["VP of Sales", "Sales Development Rep", "AI Engineer"],
        "hiring_velocity": "high", "growth_yoy": 2.5,
        "recent_news": "Raised $10M Series A as AI conversation intelligence for field sales explodes",
        "description": "AI speech analytics for outside sales and field service teams",
        "icp_tags": ["ai-saas", "sales-tech", "series-a", "high-growth"],
        "competitors": ["Gong", "Chorus", "Salesloft"],
        "key_contacts": [{"name": "Sebastian Jimenez", "title": "CEO"}]
    },
    {
        "id": "comp_048", "name": "Labelbox", "domain": "labelbox.com",
        "industry": "AI SaaS", "sub_industry": "Data Labeling / RLHF",
        "company_size": 250, "size_band": "mid-market", "geography": "US", "hq_city": "San Francisco",
        "funding_stage": "Series D", "total_funding_usd": 188_000_000, "last_funding_date": "2022-01-05",
        "revenue_range": "$10M-$50M", "tech_stack": ["GCP", "Python", "React", "PostgreSQL", "PyTorch"],
        "hiring_roles": ["Enterprise Account Executive", "ML Solutions Engineer", "Data Ops Manager"],
        "hiring_velocity": "medium", "growth_yoy": 0.5,
        "recent_news": "Partnering with AI labs for RLHF human feedback pipelines",
        "description": "Data-centric AI platform for training data labeling and model iteration",
        "icp_tags": ["ai-saas", "data-labeling", "series-d", "ml-infra"],
        "competitors": ["Scale AI", "Snorkel", "Appen"],
        "key_contacts": [{"name": "Manu Sharma", "title": "CEO"}]
    },
    {
        "id": "comp_049", "name": "Weights & Biases", "domain": "wandb.ai",
        "industry": "AI SaaS", "sub_industry": "MLOps",
        "company_size": 300, "size_band": "mid-market", "geography": "US", "hq_city": "San Francisco",
        "funding_stage": "Series C", "total_funding_usd": 250_000_000, "last_funding_date": "2023-09-20",
        "revenue_range": "$50M-$100M", "tech_stack": ["GCP", "Python", "React", "PyTorch", "TensorFlow"],
        "hiring_roles": ["VP Sales", "Enterprise Account Executive", "ML Research Engineer"],
        "hiring_velocity": "high", "growth_yoy": 0.9,
        "recent_news": "Reached 1M+ users as LLM fine-tuning adoption accelerates",
        "description": "MLOps platform for experiment tracking, model registry, and LLM evaluation",
        "icp_tags": ["ai-saas", "mlops", "series-c", "high-growth"],
        "competitors": ["MLflow", "Comet ML", "Neptune.ai"],
        "key_contacts": [{"name": "Lukas Biewald", "title": "CEO"}]
    },
    {
        "id": "comp_050", "name": "Modal Labs", "domain": "modal.com",
        "industry": "AI SaaS", "sub_industry": "Serverless GPU Compute",
        "company_size": 35, "size_band": "startup", "geography": "US", "hq_city": "New York",
        "funding_stage": "Series B", "total_funding_usd": 45_000_000, "last_funding_date": "2026-03-01",
        "revenue_range": "$1M-$5M", "tech_stack": ["AWS", "Python", "Kubernetes", "CUDA", "gVisor"],
        "hiring_roles": ["Head of Revenue", "Developer Advocate", "Infrastructure Engineer"],
        "hiring_velocity": "high", "growth_yoy": 3.0,
        "recent_news": "Raised $45M Series B as AI compute demand surges for inference workloads",
        "description": "Serverless cloud platform for AI/ML workloads with GPU support",
        "icp_tags": ["ai-infra", "serverless", "series-b", "high-growth"],
        "competitors": ["Banana.dev", "Replicate", "RunPod"],
        "key_contacts": [{"name": "Erik Bernhardsson", "title": "CEO"}]
    },
]


# ---------------------------------------------------------------------------
# Schema definition (used by Critic Agent for hallucination detection)
# ---------------------------------------------------------------------------

SCHEMA: Dict[str, Any] = {
    "fields": {
        "industry": {
            "type": "string",
            "valid_values": [
                "SaaS", "AI SaaS", "FinTech", "DevTools", "HR Tech",
                "Cloud", "Security", "Analytics", "MarTech"
            ],
            "fuzzy_match": True,
        },
        "geography": {
            "type": "string",
            "valid_values": ["US", "UK", "Germany", "Canada", "Australia", "France", "India", "Singapore"],
            "fuzzy_match": True,
        },
        "funding_stage": {
            "type": "string",
            "valid_values": [e.value for e in FundingStage],  # includes Series E, Series F
            "fuzzy_match": False,
        },
        "size_band": {
            "type": "string",
            "valid_values": [e.value for e in SizeBand],
            "fuzzy_match": False,
        },
        "hiring_velocity": {
            "type": "string",
            "valid_values": [e.value for e in HiringVelocity],
            "fuzzy_match": False,
        },
        "company_size_min": {"type": "int"},
        "company_size_max": {"type": "int"},
        "tech_stack": {"type": "list[string]"},
        "hiring_roles": {"type": "list[string]"},
        "growth_signal": {"type": "string", "valid_values": ["high", "medium", "low"]},
        "revenue_range": {"type": "string"},
    },
    "invalid_fields": [
        "ipo_stage", "unicorn_status", "valuation", "founding_year",
        "employee_growth_percent", "churn_rate",
    ],
}


# ---------------------------------------------------------------------------
# Mock Data API
# ---------------------------------------------------------------------------

class MockDataAPI:
    def __init__(self) -> None:
        self._companies = [self._parse(c) for c in _RAW_COMPANIES]

    def _parse(self, raw: Dict[str, Any]) -> CompanyRecord:
        contacts = [KeyContact(**c) for c in raw.get("key_contacts", [])]
        return CompanyRecord(
            id=raw["id"],
            name=raw["name"],
            domain=raw["domain"],
            industry=raw["industry"],
            sub_industry=raw.get("sub_industry", ""),
            company_size=raw["company_size"],
            size_band=SizeBand(raw["size_band"]),
            geography=raw["geography"],
            hq_city=raw["hq_city"],
            funding_stage=FundingStage(raw["funding_stage"]),
            total_funding_usd=raw.get("total_funding_usd", 0),
            last_funding_date=raw.get("last_funding_date"),
            revenue_range=raw.get("revenue_range", ""),
            tech_stack=raw.get("tech_stack", []),
            hiring_roles=raw.get("hiring_roles", []),
            hiring_velocity=HiringVelocity(raw.get("hiring_velocity", "none")),
            growth_yoy=raw.get("growth_yoy", 0.0),
            recent_news=raw.get("recent_news", ""),
            description=raw.get("description", ""),
            icp_tags=raw.get("icp_tags", []),
            competitors=raw.get("competitors", []),
            key_contacts=contacts,
        )

    def get_schema(self) -> Dict[str, Any]:
        return SCHEMA

    def get_company_by_id(self, company_id: str) -> Optional[CompanyRecord]:
        for c in self._companies:
            if c.id == company_id:
                return c
        return None

    def query_companies(self, filters: Dict[str, Any]) -> List[CompanyRecord]:
        results = list(self._companies)
        for key, value in filters.items():
            if value is None:
                continue
            results = self._apply_filter(results, key, value)
        return self._rank_results(results, filters)

    def _apply_filter(self, companies: List[CompanyRecord], key: str, value: Any) -> List[CompanyRecord]:
        out = []
        for c in companies:
            if key == "industry":
                if self._fuzzy_contains(c.industry, value) or self._fuzzy_contains(c.sub_industry, value):
                    out.append(c)
            elif key == "geography":
                if self._fuzzy_contains(c.geography, value):
                    out.append(c)
            elif key == "funding_stage":
                if c.funding_stage.value.lower() == str(value).lower():
                    out.append(c)
            elif key == "company_size_min":
                if c.company_size >= int(value):
                    out.append(c)
            elif key == "company_size_max":
                if c.company_size <= int(value):
                    out.append(c)
            elif key == "size_band":
                if c.size_band.value.lower() == str(value).lower():
                    out.append(c)
            elif key == "tech_stack":
                vals = [value] if isinstance(value, str) else value
                if any(t.lower() in [v.lower() for v in c.tech_stack] for t in vals):
                    out.append(c)
            elif key == "hiring_roles":
                vals = [value] if isinstance(value, str) else value
                if any(
                    any(v.lower() in r.lower() for r in c.hiring_roles)
                    for v in vals
                ):
                    out.append(c)
            elif key == "hiring_velocity":
                if c.hiring_velocity.value.lower() == str(value).lower():
                    out.append(c)
            elif key == "growth_signal":
                if value == "high" and c.growth_yoy >= 0.5:
                    out.append(c)
                elif value == "medium" and 0.2 <= c.growth_yoy < 0.5:
                    out.append(c)
                elif value == "low" and c.growth_yoy < 0.2:
                    out.append(c)
            else:
                # Unknown filter — pass through (Critic will flag it)
                out.append(c)
        return out

    @staticmethod
    def _fuzzy_contains(field: str, query: str) -> bool:
        return query.lower() in field.lower() or field.lower() in query.lower()

    def _rank_results(self, companies: List[CompanyRecord], filters: Dict[str, Any]) -> List[CompanyRecord]:
        def score(c: CompanyRecord) -> float:
            s = 0.0
            if c.hiring_velocity == HiringVelocity.HIGH:
                s += 2.0
            if c.growth_yoy > 0.5:
                s += 1.5
            if c.funding_stage in (FundingStage.SERIES_A, FundingStage.SERIES_B, FundingStage.SERIES_C):
                s += 1.0
            return s

        return sorted(companies, key=score, reverse=True)
