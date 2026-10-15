import 'package:flutter/material.dart';

import '../core/sage_api.dart';
import '../theme/sage_theme.dart';

String? _requiredField(String? value) =>
    value == null || value.trim().isEmpty ? 'This field is required.' : null;

String _npr(dynamic value) {
  if (value is num) return 'NPR ${value.round()}';
  return 'Price not set';
}

class JobsScreen extends StatefulWidget {
  const JobsScreen({required this.api, super.key});
  final SageApi api;

  @override
  State<JobsScreen> createState() => _JobsScreenState();
}

class _JobsScreenState extends State<JobsScreen> {
  int _mode = 0;
  bool _loading = false;
  Object? _error;
  List<dynamic> _items = const [];
  final TextEditingController _searchController = TextEditingController();
  final TextEditingController _locationSearchController = TextEditingController();
  // These controllers are screen-owned so they remain alive until the dialog
  // reverse transition has removed its widgets from the overlay.
  final TextEditingController _applicationNoteController = TextEditingController();
  final TextEditingController _jobTitleController = TextEditingController();
  final TextEditingController _jobCompanyController = TextEditingController();
  final TextEditingController _jobDescriptionController = TextEditingController();
  final TextEditingController _jobLocationController = TextEditingController();
  final TextEditingController _jobSalaryMinController = TextEditingController();
  final TextEditingController _jobSalaryMaxController = TextEditingController();

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _searchController.dispose();
    _locationSearchController.dispose();
    _applicationNoteController.dispose();
    _jobTitleController.dispose();
    _jobCompanyController.dispose();
    _jobDescriptionController.dispose();
    _jobLocationController.dispose();
    _jobSalaryMinController.dispose();
    _jobSalaryMaxController.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    if (!mounted) return;
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final items = switch (_mode) {
        0 => await widget.api.jobPostings(
            query: _searchController.text,
            location: _locationSearchController.text,
          ),
        1 => await widget.api.myJobPostings(),
        _ => await widget.api.myJobApplications(),
      };
      if (!mounted) return;
      setState(() {
        _items = items;
        _error = null;
      });
    } catch (error) {
      if (!mounted) return;
      setState(() => _error = error);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  void _changeMode(int value) {
    if (_mode == value) return;
    setState(() {
      _mode = value;
      _items = const [];
      _error = null;
    });
    _load();
  }

  Future<void> _apply(Map<String, dynamic> job) async {
    _applicationNoteController.clear();
    final note = await showDialog<String>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('Apply for this job'),
        content: TextField(
          controller: _applicationNoteController,
          minLines: 2,
          maxLines: 5,
          decoration: const InputDecoration(
            labelText: 'Short introduction (optional)',
            hintText: 'Share relevant skills or experience',
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dialogContext),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(dialogContext, _applicationNoteController.text.trim()),
            child: const Text('Submit application'),
          ),
        ],
      ),
    );
    if (note == null || !mounted) return;
    try {
      await widget.api.applyForJob(job['id'].toString(), coverNote: note);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Application submitted successfully.')),
      );
      if (_mode == 2) await _load();
    } catch (error) {
      _message('Could not apply: $error');
    }
  }

  Future<void> _closeJob(Map<String, dynamic> job) async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('Close job posting?'),
        content: const Text('Applicants will no longer be able to apply to this listing.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(dialogContext, false), child: const Text('Cancel')),
          FilledButton(onPressed: () => Navigator.pop(dialogContext, true), child: const Text('Close posting')),
        ],
      ),
    );
    if (confirm != true) return;
    try {
      await widget.api.closeJobPosting(job['id'].toString());
      if (!mounted) return;
      _message('Job posting closed.');
      await _load();
    } catch (error) {
      _message('Could not close job: $error');
    }
  }

  Future<void> _viewApplicants(Map<String, dynamic> job) async {
    try {
      final response = await widget.api.jobApplications(job['id'].toString());
      if (!mounted) return;
      final applications = response['applications'] is List
          ? List<dynamic>.from(response['applications'] as List)
          : <dynamic>[];
      await showDialog<void>(
        context: context,
        builder: (dialogContext) => AlertDialog(
          title: Text('Applicants • ${job['title'] ?? 'Job'}'),
          content: SizedBox(
            width: 440,
            child: applications.isEmpty
                ? const Text('No applications received yet.')
                : ListView.separated(
                    shrinkWrap: true,
                    itemCount: applications.length,
                    separatorBuilder: (_, _) => const Divider(),
                    itemBuilder: (_, index) {
                      final raw = applications[index];
                      final item = raw is Map ? Map<String, dynamic>.from(raw) : <String, dynamic>{};
                      final note = (item['cover_note'] ?? '').toString();
                      return ListTile(
                        leading: const CircleAvatar(child: Icon(Icons.person_outline)),
                        title: Text((item['applicant_name'] ?? 'Applicant').toString()),
                        subtitle: Text(note.isEmpty ? 'No introduction provided.' : note),
                        trailing: Text((item['status'] ?? '').toString()),
                      );
                    },
                  ),
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(dialogContext), child: const Text('Done')),
          ],
        ),
      );
    } catch (error) {
      _message('Could not load applicants: $error');
    }
  }

  Future<void> _createJob() async {
    final formKey = GlobalKey<FormState>();
    final title = _jobTitleController..clear();
    final company = _jobCompanyController..clear();
    final description = _jobDescriptionController..clear();
    final location = _jobLocationController..clear();
    final salaryMin = _jobSalaryMinController..clear();
    final salaryMax = _jobSalaryMaxController..clear();
    var employmentType = 'full_time';
    var saving = false;
    String? formError;

    final created = await showDialog<bool>(
      context: context,
      barrierDismissible: false,
      builder: (dialogContext) => StatefulBuilder(
        builder: (dialogContext, setDialogState) => AlertDialog(
          title: const Text('Post a job'),
          content: SizedBox(
            width: 520,
            child: SingleChildScrollView(
              child: Form(
                key: formKey,
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    TextFormField(
                      controller: title,
                      autofocus: true,
                      decoration: const InputDecoration(labelText: 'Job title'),
                      validator: _requiredField,
                    ),
                    TextFormField(
                      controller: company,
                      decoration: const InputDecoration(labelText: 'Company / employer'),
                      validator: _requiredField,
                    ),
                    TextFormField(
                      controller: description,
                      minLines: 3,
                      maxLines: 6,
                      decoration: const InputDecoration(labelText: 'Job description'),
                      validator: _requiredField,
                    ),
                    TextFormField(
                      controller: location,
                      decoration: const InputDecoration(labelText: 'Location (e.g. Kathmandu or Remote)'),
                      validator: _requiredField,
                    ),
                    const SizedBox(height: 10),
                    DropdownButtonFormField<String>(
                      value: employmentType,
                      decoration: const InputDecoration(labelText: 'Work type'),
                      items: const [
                        DropdownMenuItem(value: 'full_time', child: Text('Full-time')),
                        DropdownMenuItem(value: 'part_time', child: Text('Part-time')),
                        DropdownMenuItem(value: 'contract', child: Text('Contract')),
                        DropdownMenuItem(value: 'internship', child: Text('Internship')),
                        DropdownMenuItem(value: 'remote', child: Text('Remote')),
                        DropdownMenuItem(value: 'temporary', child: Text('Temporary')),
                      ],
                      onChanged: saving ? null : (value) => setDialogState(() => employmentType = value ?? 'full_time'),
                    ),
                    Row(
                      children: [
                        Expanded(
                          child: TextFormField(
                            controller: salaryMin,
                            keyboardType: const TextInputType.numberWithOptions(decimal: false),
                            decoration: const InputDecoration(labelText: 'Min salary (NPR)', prefixText: 'Rs '),
                            validator: (value) {
                              if (value == null || value.trim().isEmpty) return null;
                              final parsed = double.tryParse(value.trim());
                              return parsed == null || parsed < 0 ? 'Enter a valid amount.' : null;
                            },
                          ),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: TextFormField(
                            controller: salaryMax,
                            keyboardType: const TextInputType.numberWithOptions(decimal: false),
                            decoration: const InputDecoration(labelText: 'Max salary (NPR)', prefixText: 'Rs '),
                            validator: (value) {
                              if (value == null || value.trim().isEmpty) return null;
                              final parsed = double.tryParse(value.trim());
                              if (parsed == null || parsed < 0) return 'Enter a valid amount.';
                              final minimum = double.tryParse(salaryMin.text.trim());
                              if (minimum != null && parsed < minimum) return 'Must be ≥ minimum salary.';
                              return null;
                            },
                          ),
                        ),
                      ],
                    ),
                    if (formError != null) ...[
                      const SizedBox(height: 12),
                      Align(
                        alignment: Alignment.centerLeft,
                        child: Text(formError!, style: const TextStyle(color: SageTheme.failure)),
                      ),
                    ],
                  ],
                ),
              ),
            ),
          ),
          actions: [
            TextButton(
              onPressed: saving ? null : () => Navigator.pop(dialogContext, false),
              child: const Text('Cancel'),
            ),
            FilledButton(
              onPressed: saving
                  ? null
                  : () async {
                      if (!(formKey.currentState?.validate() ?? false)) return;
                      setDialogState(() {
                        saving = true;
                        formError = null;
                      });
                      try {
                        await widget.api.createJobPosting(
                          title: title.text.trim(),
                          company: company.text.trim(),
                          description: description.text.trim(),
                          location: location.text.trim(),
                          employmentType: employmentType,
                          salaryMinNpr: double.tryParse(salaryMin.text.trim()),
                          salaryMaxNpr: double.tryParse(salaryMax.text.trim()),
                        );
                        if (dialogContext.mounted) Navigator.pop(dialogContext, true);
                      } catch (error) {
                        if (dialogContext.mounted) {
                          setDialogState(() {
                            saving = false;
                            formError = 'Could not post the job: $error';
                          });
                        }
                      }
                    },
              child: saving
                  ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2))
                  : const Text('Publish job'),
            ),
          ],
        ),
      ),
    );
    if (created == true && mounted) {
      setState(() => _mode = 1);
      await _load();
    }
  }

  void _message(String value) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(value)));
  }

  Widget _modeChip(int value, String label) => Padding(
        padding: const EdgeInsets.only(right: 8),
        child: ChoiceChip(
          label: Text(label),
          selected: _mode == value,
          onSelected: (_) => _changeMode(value),
        ),
      );

  Widget _jobCard(dynamic raw) {
    final item = raw is Map ? Map<String, dynamic>.from(raw) : <String, dynamic>{};
    if (_mode == 2) {
      final rawJob = item['job'];
      final job = rawJob is Map ? Map<String, dynamic>.from(rawJob) : <String, dynamic>{};
      return Card(
        child: ListTile(
          leading: const Icon(Icons.assignment_outlined, color: SageTheme.cyan),
          title: Text((job['title'] ?? 'Job application').toString()),
          subtitle: Text('${job['company'] ?? 'Employer'} • Application: ${item['status'] ?? 'submitted'}'),
          trailing: const Icon(Icons.chevron_right),
        ),
      );
    }

    final title = (item['title'] ?? 'Job opportunity').toString();
    final company = (item['company'] ?? item['employer_name'] ?? 'Employer').toString();
    final location = (item['location'] ?? 'Location not specified').toString();
    final type = (item['employment_type'] ?? 'full_time').toString().replaceAll('_', ' ');
    final min = item['salary_min_npr'];
    final max = item['salary_max_npr'];
    final salary = min == null && max == null
        ? 'Salary not specified'
        : '${min == null ? '' : _npr(min)}${min != null && max != null ? ' – ' : ''}${max == null ? '' : _npr(max)}';
    final open = item['status'] == 'open';
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(15),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(title, style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w800)),
            const SizedBox(height: 5),
            Text(company, style: const TextStyle(color: SageTheme.cyan, fontWeight: FontWeight.w600)),
            const SizedBox(height: 8),
            Wrap(
              spacing: 12,
              runSpacing: 6,
              children: [
                _meta(Icons.location_on_outlined, location),
                _meta(Icons.schedule, type),
                _meta(Icons.payments_outlined, salary),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              (item['description'] ?? '').toString(),
              maxLines: 4,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(color: SageTheme.textSecondary, height: 1.35),
            ),
            const SizedBox(height: 10),
            if (_mode == 0)
              Align(
                alignment: Alignment.centerRight,
                child: FilledButton.icon(
                  onPressed: open ? () => _apply(item) : null,
                  icon: const Icon(Icons.send_outlined),
                  label: const Text('Apply'),
                ),
              )
            else
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  OutlinedButton.icon(
                    onPressed: () => _viewApplicants(item),
                    icon: const Icon(Icons.people_outline),
                    label: const Text('Applicants'),
                  ),
                  if (open)
                    TextButton.icon(
                      onPressed: () => _closeJob(item),
                      icon: const Icon(Icons.close),
                      label: const Text('Close posting'),
                    )
                  else
                    const Chip(label: Text('Closed')),
                ],
              ),
          ],
        ),
      ),
    );
  }

  Widget _meta(IconData icon, String text) => Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 15, color: SageTheme.textSecondary),
          const SizedBox(width: 4),
          Text(text, style: const TextStyle(fontSize: 12, color: SageTheme.textSecondary)),
        ],
      );

  @override
  Widget build(BuildContext context) => Scaffold(
        backgroundColor: SageTheme.voidBlack,
        appBar: AppBar(
          title: const Text('Jobs'),
          backgroundColor: Colors.transparent,
          actions: [
            IconButton(
              tooltip: 'Refresh jobs',
              onPressed: _loading ? null : _load,
              icon: const Icon(Icons.refresh),
            ),
          ],
        ),
        floatingActionButton: _mode == 1
            ? FloatingActionButton.extended(
                onPressed: _createJob,
                icon: const Icon(Icons.add),
                label: const Text('Post a job'),
              )
            : null,
        body: Column(
          children: [
            SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: Row(
                children: [
                  _modeChip(0, 'Find jobs'),
                  _modeChip(1, 'My postings'),
                  _modeChip(2, 'My applications'),
                ],
              ),
            ),
            if (_mode == 0)
              Padding(
                padding: const EdgeInsets.fromLTRB(16, 8, 16, 4),
                child: Column(
                  children: [
                    Row(
                      children: [
                        Expanded(
                          child: TextField(
                            controller: _searchController,
                            onSubmitted: (_) => _load(),
                            decoration: const InputDecoration(
                              hintText: 'Search title, company or description',
                              prefixIcon: Icon(Icons.search),
                            ),
                          ),
                        ),
                        const SizedBox(width: 8),
                        IconButton.filled(
                          tooltip: 'Search jobs',
                          onPressed: _load,
                          icon: const Icon(Icons.search),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    TextField(
                      controller: _locationSearchController,
                      onSubmitted: (_) => _load(),
                      decoration: const InputDecoration(
                        hintText: 'Filter by city, district or Remote',
                        prefixIcon: Icon(Icons.location_on_outlined),
                      ),
                    ),
                  ],
                ),
              ),
            if (_loading) const LinearProgressIndicator(),
            if (_error != null)
              Padding(
                padding: const EdgeInsets.all(12),
                child: Card(
                  child: ListTile(
                    leading: const Icon(Icons.cloud_off_outlined, color: SageTheme.failure),
                    title: const Text('Could not load jobs'),
                    subtitle: Text(_error.toString()),
                    trailing: TextButton(onPressed: _load, child: const Text('Retry')),
                  ),
                ),
              ),
            Expanded(
              child: _loading && _items.isEmpty
                  ? const Center(child: CircularProgressIndicator())
                  : _items.isEmpty && _error == null
                      ? Center(
                          child: Padding(
                            padding: const EdgeInsets.all(28),
                            child: Text(
                              switch (_mode) {
                                0 => 'No open jobs found yet. Try a different search or check again later.',
                                1 => 'You have not posted any jobs yet. Post your first opening here.',
                                _ => 'Your job applications will appear here.',
                              },
                              textAlign: TextAlign.center,
                              style: const TextStyle(color: SageTheme.textSecondary, height: 1.45),
                            ),
                          ),
                        )
                      : ListView.builder(
                          padding: const EdgeInsets.fromLTRB(14, 8, 14, 100),
                          itemCount: _items.length,
                          itemBuilder: (_, index) => _jobCard(_items[index]),
                        ),
            ),
          ],
        ),
      );
}

class MarketplaceScreen extends StatefulWidget {
  const MarketplaceScreen({required this.api, super.key});
  final SageApi api;

  @override
  State<MarketplaceScreen> createState() => _MarketplaceScreenState();
}

class _MarketplaceScreenState extends State<MarketplaceScreen> {
  int _mode = 0;
  bool _loading = false;
  Object? _error;
  List<dynamic> _items = const [];
  String? _categoryFilter;
  final TextEditingController _searchController = TextEditingController();
  final TextEditingController _locationSearchController = TextEditingController();
  final TextEditingController _listingTitleController = TextEditingController();
  final TextEditingController _listingDescriptionController = TextEditingController();
  final TextEditingController _listingLocationController = TextEditingController();
  final TextEditingController _listingPriceController = TextEditingController();
  final TextEditingController _inquiryMessageController = TextEditingController();

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _searchController.dispose();
    _locationSearchController.dispose();
    _listingTitleController.dispose();
    _listingDescriptionController.dispose();
    _listingLocationController.dispose();
    _listingPriceController.dispose();
    _inquiryMessageController.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    if (!mounted) return;
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final items = switch (_mode) {
        0 => await widget.api.marketplaceListings(
            query: _searchController.text,
            category: _categoryFilter,
            location: _locationSearchController.text,
          ),
        1 => await widget.api.myMarketplaceListings(),
        _ => await widget.api.myMarketplaceInquiries(),
      };
      if (!mounted) return;
      setState(() {
        _items = items;
        _error = null;
      });
    } catch (error) {
      if (!mounted) return;
      setState(() => _error = error);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  void _changeMode(int value) {
    if (_mode == value) return;
    setState(() {
      _mode = value;
      _items = const [];
      _error = null;
    });
    _load();
  }

  void _message(String value) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(value)));
  }

  Widget _modeChip(int value, String label) => Padding(
        padding: const EdgeInsets.only(right: 8),
        child: ChoiceChip(
          label: Text(label),
          selected: _mode == value,
          onSelected: (_) => _changeMode(value),
        ),
      );

  Future<void> _createListing() async {
    final formKey = GlobalKey<FormState>();
    final title = _listingTitleController..clear();
    final description = _listingDescriptionController..clear();
    final location = _listingLocationController..clear();
    final price = _listingPriceController..clear();
    var category = 'vehicles';
    var condition = 'used';
    var saving = false;
    String? formError;

    final created = await showDialog<bool>(
      context: context,
      barrierDismissible: false,
      builder: (dialogContext) => StatefulBuilder(
        builder: (dialogContext, setDialogState) => AlertDialog(
          title: const Text('Create marketplace listing'),
          content: SizedBox(
            width: 520,
            child: SingleChildScrollView(
              child: Form(
                key: formKey,
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    TextFormField(
                      controller: title,
                      autofocus: true,
                      decoration: const InputDecoration(labelText: 'Listing title'),
                      validator: _requiredField,
                    ),
                    DropdownButtonFormField<String>(
                      value: category,
                      decoration: const InputDecoration(labelText: 'Category'),
                      items: const [
                        DropdownMenuItem(value: 'vehicles', child: Text('Vehicles / scooters')),
                        DropdownMenuItem(value: 'electronics', child: Text('Phones / electronics')),
                        DropdownMenuItem(value: 'property', child: Text('Houses / land / property')),
                        DropdownMenuItem(value: 'services', child: Text('Services')),
                        DropdownMenuItem(value: 'courses', child: Text('Courses')),
                        DropdownMenuItem(value: 'home', child: Text('Home and living')),
                        DropdownMenuItem(value: 'other', child: Text('Other')),
                      ],
                      onChanged: saving ? null : (value) => setDialogState(() => category = value ?? 'other'),
                    ),
                    TextFormField(
                      controller: description,
                      minLines: 3,
                      maxLines: 6,
                      decoration: const InputDecoration(labelText: 'Description'),
                      validator: _requiredField,
                    ),
                    TextFormField(
                      controller: location,
                      decoration: const InputDecoration(labelText: 'Location'),
                      validator: _requiredField,
                    ),
                    TextFormField(
                      controller: price,
                      keyboardType: const TextInputType.numberWithOptions(decimal: false),
                      decoration: const InputDecoration(labelText: 'Price in NPR', prefixText: 'Rs '),
                      validator: (value) {
                        if (value == null || value.trim().isEmpty) return 'Price is required.';
                        final amount = double.tryParse(value.trim());
                        if (amount == null || amount <= 0) return 'Enter a price greater than zero.';
                        return null;
                      },
                    ),
                    DropdownButtonFormField<String>(
                      value: condition,
                      decoration: const InputDecoration(labelText: 'Condition'),
                      items: const [
                        DropdownMenuItem(value: 'new', child: Text('New')),
                        DropdownMenuItem(value: 'used', child: Text('Used')),
                        DropdownMenuItem(value: 'service', child: Text('Service / course')),
                      ],
                      onChanged: saving ? null : (value) => setDialogState(() => condition = value ?? 'used'),
                    ),
                    if (formError != null) ...[
                      const SizedBox(height: 12),
                      Align(
                        alignment: Alignment.centerLeft,
                        child: Text(formError!, style: const TextStyle(color: SageTheme.failure)),
                      ),
                    ],
                  ],
                ),
              ),
            ),
          ),
          actions: [
            TextButton(onPressed: saving ? null : () => Navigator.pop(dialogContext, false), child: const Text('Cancel')),
            FilledButton(
              onPressed: saving
                  ? null
                  : () async {
                      if (!(formKey.currentState?.validate() ?? false)) return;
                      setDialogState(() {
                        saving = true;
                        formError = null;
                      });
                      try {
                        await widget.api.createMarketplaceListing(
                          title: title.text.trim(),
                          category: category,
                          description: description.text.trim(),
                          location: location.text.trim(),
                          priceNpr: double.parse(price.text.trim()),
                          itemCondition: condition,
                        );
                        if (dialogContext.mounted) Navigator.pop(dialogContext, true);
                      } catch (error) {
                        if (dialogContext.mounted) {
                          setDialogState(() {
                            saving = false;
                            formError = 'Could not publish listing: $error';
                          });
                        }
                      }
                    },
              child: saving
                  ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2))
                  : const Text('Publish listing'),
            ),
          ],
        ),
      ),
    );
    if (created == true && mounted) {
      setState(() => _mode = 1);
      await _load();
    }
  }

  Future<void> _inquire(Map<String, dynamic> listing) async {
    _inquiryMessageController.clear();
    var sending = false;
    String? errorMessage;
    final sent = await showDialog<bool>(
      context: context,
      barrierDismissible: false,
      builder: (dialogContext) => StatefulBuilder(
        builder: (dialogContext, setDialogState) => AlertDialog(
          title: const Text('Contact seller'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text((listing['title'] ?? 'Listing').toString(), style: const TextStyle(fontWeight: FontWeight.w700)),
              const SizedBox(height: 10),
              TextField(
                controller: _inquiryMessageController,
                minLines: 2,
                maxLines: 5,
                onChanged: (_) => setDialogState(() => errorMessage = null),
                decoration: const InputDecoration(
                  labelText: 'Message',
                  hintText: 'Ask a question or arrange a viewing',
                ),
              ),
              if (errorMessage != null) ...[
                const SizedBox(height: 8),
                Text(errorMessage!, style: const TextStyle(color: SageTheme.failure)),
              ],
            ],
          ),
          actions: [
            TextButton(onPressed: sending ? null : () => Navigator.pop(dialogContext, false), child: const Text('Cancel')),
            FilledButton(
              onPressed: _inquiryMessageController.text.trim().isEmpty || sending
                  ? null
                  : () async {
                      setDialogState(() => sending = true);
                      try {
                        await widget.api.inquireMarketplaceListing(
                          listing['id'].toString(),
                          message: _inquiryMessageController.text.trim(),
                        );
                        if (dialogContext.mounted) Navigator.pop(dialogContext, true);
                      } catch (error) {
                        if (dialogContext.mounted) {
                          setDialogState(() {
                            sending = false;
                            errorMessage = 'Could not send inquiry: $error';
                          });
                        }
                      }
                    },
              child: sending
                  ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2))
                  : const Text('Send inquiry'),
            ),
          ],
        ),
      ),
    );
    if (sent == true && mounted) {
      _message('Your inquiry was sent to the seller.');
      if (_mode == 2) await _load();
    }
  }

  Future<void> _viewInquiries(Map<String, dynamic> listing) async {
    try {
      final response = await widget.api.marketplaceListingInquiries(listing['id'].toString());
      if (!mounted) return;
      final inquiries = response['inquiries'] is List
          ? List<dynamic>.from(response['inquiries'] as List)
          : <dynamic>[];
      await showDialog<void>(
        context: context,
        builder: (dialogContext) => AlertDialog(
          title: Text('Interest • ${listing['title'] ?? 'Listing'}'),
          content: SizedBox(
            width: 440,
            child: inquiries.isEmpty
                ? const Text('No buyer inquiries yet.')
                : ListView.separated(
                    shrinkWrap: true,
                    itemCount: inquiries.length,
                    separatorBuilder: (_, _) => const Divider(),
                    itemBuilder: (_, index) {
                      final raw = inquiries[index];
                      final item = raw is Map ? Map<String, dynamic>.from(raw) : <String, dynamic>{};
                      return ListTile(
                        leading: const Icon(Icons.person_outline),
                        title: Text((item['buyer_name'] ?? 'Buyer').toString()),
                        subtitle: Text((item['message'] ?? '').toString()),
                      );
                    },
                  ),
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(dialogContext), child: const Text('Done')),
          ],
        ),
      );
    } catch (error) {
      _message('Could not load seller inquiries: $error');
    }
  }

  Future<void> _closeListing(Map<String, dynamic> listing) async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('Close this listing?'),
        content: const Text('The listing will no longer accept new inquiries. No payment will be taken.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(dialogContext, false), child: const Text('Cancel')),
          FilledButton(onPressed: () => Navigator.pop(dialogContext, true), child: const Text('Close listing')),
        ],
      ),
    );
    if (confirm != true) return;
    try {
      await widget.api.closeMarketplaceListing(listing['id'].toString());
      if (!mounted) return;
      _message('Listing closed.');
      await _load();
    } catch (error) {
      _message('Could not close listing: $error');
    }
  }

  Widget _listingCard(dynamic raw) {
    final item = raw is Map ? Map<String, dynamic>.from(raw) : <String, dynamic>{};
    if (_mode == 2) {
      final rawListing = item['listing'];
      final listing = rawListing is Map ? Map<String, dynamic>.from(rawListing) : <String, dynamic>{};
      return Card(
        child: ListTile(
          leading: const Icon(Icons.mark_email_read_outlined, color: SageTheme.cyan),
          title: Text((listing['title'] ?? 'Marketplace interest').toString()),
          subtitle: Text('${listing['seller_name'] ?? 'Seller'} • ${item['status'] ?? 'open'}'),
        ),
      );
    }

    final title = (item['title'] ?? 'Marketplace listing').toString();
    final location = (item['location'] ?? 'Location not specified').toString();
    final category = (item['category'] ?? 'other').toString();
    final status = (item['status'] ?? '').toString();
    final condition = (item['item_condition'] ?? 'used').toString();
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(15),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(title, style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w800)),
            const SizedBox(height: 5),
            Text(_npr(item['price_npr']), style: const TextStyle(color: SageTheme.cyan, fontSize: 17, fontWeight: FontWeight.w800)),
            const SizedBox(height: 8),
            Wrap(
              spacing: 12,
              runSpacing: 6,
              children: [
                _listingMeta(Icons.category_outlined, category),
                _listingMeta(Icons.location_on_outlined, location),
                _listingMeta(Icons.inventory_2_outlined, condition),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              (item['description'] ?? '').toString(),
              maxLines: 4,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(color: SageTheme.textSecondary, height: 1.35),
            ),
            const SizedBox(height: 6),
            Text('Seller: ${item['seller_name'] ?? 'SAGE user'}', style: const TextStyle(color: SageTheme.textSecondary, fontSize: 12)),
            const SizedBox(height: 10),
            if (_mode == 0)
              Align(
                alignment: Alignment.centerRight,
                child: FilledButton.icon(
                  onPressed: status == 'active' ? () => _inquire(item) : null,
                  icon: const Icon(Icons.chat_bubble_outline),
                  label: const Text('Contact seller'),
                ),
              )
            else
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  OutlinedButton.icon(
                    onPressed: () => _viewInquiries(item),
                    icon: const Icon(Icons.mark_email_unread_outlined),
                    label: const Text('View inquiries'),
                  ),
                  if (status == 'active')
                    TextButton.icon(
                      onPressed: () => _closeListing(item),
                      icon: const Icon(Icons.close),
                      label: const Text('Close listing'),
                    )
                  else
                    const Chip(label: Text('Closed')),
                ],
              ),
          ],
        ),
      ),
    );
  }

  Widget _listingMeta(IconData icon, String text) => Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 15, color: SageTheme.textSecondary),
          const SizedBox(width: 4),
          Text(text, style: const TextStyle(fontSize: 12, color: SageTheme.textSecondary)),
        ],
      );

  @override
  Widget build(BuildContext context) => Scaffold(
        backgroundColor: SageTheme.voidBlack,
        appBar: AppBar(
          title: const Text('Marketplace'),
          backgroundColor: Colors.transparent,
          actions: [
            IconButton(
              tooltip: 'Refresh marketplace',
              onPressed: _loading ? null : _load,
              icon: const Icon(Icons.refresh),
            ),
          ],
        ),
        floatingActionButton: _mode == 1
            ? FloatingActionButton.extended(
                onPressed: _createListing,
                icon: const Icon(Icons.add),
                label: const Text('Sell an item'),
              )
            : null,
        body: Column(
          children: [
            SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: Row(
                children: [
                  _modeChip(0, 'Browse'),
                  _modeChip(1, 'My listings'),
                  _modeChip(2, 'My interest'),
                ],
              ),
            ),
            if (_mode == 0)
              Padding(
                padding: const EdgeInsets.fromLTRB(16, 8, 16, 4),
                child: Column(
                  children: [
                    Row(
                      children: [
                        Expanded(
                          child: TextField(
                            controller: _searchController,
                            onSubmitted: (_) => _load(),
                            decoration: const InputDecoration(
                              hintText: 'Search items, services and courses',
                              prefixIcon: Icon(Icons.search),
                            ),
                          ),
                        ),
                        const SizedBox(width: 8),
                        IconButton.filled(
                          tooltip: 'Search marketplace',
                          onPressed: _load,
                          icon: const Icon(Icons.search),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Row(
                      children: [
                        Expanded(
                          child: DropdownButtonFormField<String>(
                            value: _categoryFilter ?? '',
                            decoration: const InputDecoration(labelText: 'Category'),
                            items: const [
                              DropdownMenuItem(value: '', child: Text('All categories')),
                              DropdownMenuItem(value: 'vehicles', child: Text('Vehicles')),
                              DropdownMenuItem(value: 'electronics', child: Text('Electronics')),
                              DropdownMenuItem(value: 'property', child: Text('Property')),
                              DropdownMenuItem(value: 'services', child: Text('Services')),
                              DropdownMenuItem(value: 'courses', child: Text('Courses')),
                              DropdownMenuItem(value: 'home', child: Text('Home and living')),
                              DropdownMenuItem(value: 'other', child: Text('Other')),
                            ],
                            onChanged: (value) {
                              setState(() => _categoryFilter =
                                  value == null || value.isEmpty ? null : value);
                              _load();
                            },
                          ),
                        ),
                        const SizedBox(width: 10),
                        Expanded(
                          child: TextField(
                            controller: _locationSearchController,
                            onSubmitted: (_) => _load(),
                            decoration: const InputDecoration(
                              labelText: 'Location',
                              hintText: 'City or district',
                              prefixIcon: Icon(Icons.location_on_outlined),
                            ),
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            const Padding(
              padding: EdgeInsets.fromLTRB(16, 0, 16, 6),
              child: Align(
                alignment: Alignment.centerLeft,
                child: Text(
                  'Interest messages only • Checkout and payment settlement are not connected yet.',
                  style: TextStyle(color: SageTheme.textSecondary, fontSize: 11),
                ),
              ),
            ),
            if (_loading) const LinearProgressIndicator(),
            if (_error != null)
              Padding(
                padding: const EdgeInsets.all(12),
                child: Card(
                  child: ListTile(
                    leading: const Icon(Icons.cloud_off_outlined, color: SageTheme.failure),
                    title: const Text('Could not load marketplace'),
                    subtitle: Text(_error.toString()),
                    trailing: TextButton(onPressed: _load, child: const Text('Retry')),
                  ),
                ),
              ),
            Expanded(
              child: _loading && _items.isEmpty
                  ? const Center(child: CircularProgressIndicator())
                  : _items.isEmpty && _error == null
                      ? Center(
                          child: Padding(
                            padding: const EdgeInsets.all(28),
                            child: Text(
                              switch (_mode) {
                                0 => 'No listings found yet. Try another search or check again later.',
                                1 => 'You have not published any listings yet.',
                                _ => 'Your marketplace inquiries will appear here.',
                              },
                              textAlign: TextAlign.center,
                              style: const TextStyle(color: SageTheme.textSecondary, height: 1.45),
                            ),
                          ),
                        )
                      : ListView.builder(
                          padding: const EdgeInsets.fromLTRB(14, 8, 14, 100),
                          itemCount: _items.length,
                          itemBuilder: (_, index) => _listingCard(_items[index]),
                        ),
            ),
          ],
        ),
      );
}
