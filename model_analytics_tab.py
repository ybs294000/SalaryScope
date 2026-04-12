"""
model_analytics_tab.py
----------------------
Renders the Model Analytics tab for both App 1 and App 2.

All dependencies are injected via parameters to avoid circular imports
and prevent double-loading of cached resources.

Usage in app_resume.py:
    from model_analytics_tab import render_model_analytics_tab

    with tab_objects[4]:
        render_model_analytics_tab(
            is_app1=IS_APP1,
            # --- App 1 resources ---
            app1_model=app1_model if IS_APP1 else None,
            app1_metadata=app1_metadata if IS_APP1 else None,
            app1_classifier_metadata=app1_classifier_metadata if IS_APP1 else None,
            app1_salary_band_model=app1_salary_band_model if IS_APP1 else None,
            app1_cluster_metadata=app1_cluster_metadata_a1 if IS_APP1 else None,
            app1_analytics_loader=load_app1_analytics,
            assoc_rules=assoc_rules_a1_v2 if IS_APP1 else None,
            df_app1=df_app1 if IS_APP1 else None,
            APP1_MODEL_COMPARISON=APP1_MODEL_COMPARISON,
            APP1_CLASSIFIER_MODEL_COMPARISON=APP1_CLASSIFIER_MODEL_COMPARISON,
            # --- App 2 resources ---
            app2_model=app2_model if not IS_APP1 else None,
            app2_metadata=app2_metadata if not IS_APP1 else None,
            app2_analytics_loader=load_app2_analytics,
            APP2_MODEL_COMPARISON=APP2_MODEL_COMPARISON,
            # --- shared helpers ---
            apply_theme=_apply_theme,
            model_colors=_MODEL_COLORS,
            # --- pdf helpers (passed in so no re-import) ---
            cached_app1_model_analytics_pdf=cached_app1_model_analytics_pdf,
            cached_app2_model_analytics_pdf=cached_app2_model_analytics_pdf,
        )
"""

import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

# ---------------------------------------------------------------------------
# Resume NLP section (shared between app1 and app2)
# ---------------------------------------------------------------------------

def _render_resume_nlp_section():
    """
    Renders the Resume NLP Module section.
    This content is common to both App 1 and App 2 and appears in the
    Analytics tab regardless of the active model.
    """
    st.divider()

    with st.expander(":material/description: Resume NLP Module", expanded=False):

        st.caption(
            "This module processes unstructured resume text and converts it into structured "
            "features used by the machine learning model. Unlike predictive models, this is a "
            "rule-based NLP system designed for efficient and interpretable feature extraction."
        )

        st.subheader("System Overview")

        nlp_overview_df = pd.DataFrame({
            "Component": [
                "Text Extraction",
                "Text Preprocessing",
                "Experience Extraction",
                "Education Detection",
                "Skill Detection",
                "Job Title Detection",
                "Country Detection",
                "Seniority Derivation"
            ],
            "Method": [
                "pdfplumber (PDF parsing)",
                "Regex-based cleaning",
                "Regex pattern matching",
                "Rule-based keyword patterns",
                "spaCy PhraseMatcher",
                "spaCy PhraseMatcher with alias mapping",
                "spaCy NER + alias mapping",
                "Rule-based logic (experience + title)"
            ]
        })

        st.dataframe(nlp_overview_df, width='stretch')

        st.divider()
        st.subheader("NLP Processing Pipeline")

        st.markdown(
            "**Pipeline Flow:**\n\n"
            "PDF Resume &rarr; Text Extraction &rarr; Text Cleaning &rarr; "
            "NLP Processing &rarr; Feature Extraction &rarr; "
            "Structured Input &rarr; Machine Learning Model"
        )

        st.divider()
        st.subheader("Design Rationale")

        st.markdown(
            "- No labeled resume dataset was available for supervised NLP training\n"
            "- Rule-based NLP ensures deterministic and interpretable outputs\n"
            "- Faster processing compared to deep learning models\n"
            "- Suitable for extracting structured attributes (skills, experience, etc.)"
        )

        st.divider()
        st.subheader("Limitations")

        st.markdown(
            "- Performance depends on resume formatting and keyword presence\n"
            "- May miss implicit or uncommon skill expressions\n"
            "- Not designed for semantic understanding (no deep NLP model used)"
        )


# ---------------------------------------------------------------------------
# App 1 Analytics sections
# ---------------------------------------------------------------------------

@st.fragment
def _render_app1_section1_regression(
    app1_metadata,
    APP1_MODEL_COMPARISON,
    apply_theme,
    model_colors,
):
    """
    Section 1: Salary Regression Model (Random Forest)
    Covers performance metrics, model comparison, radar chart, hyperparameters,
    feature importance, and cumulative importance.
    """
    with st.expander(
        ":material/monitoring: Salary Regression Model (Random Forest)",
        expanded=True
    ):
        st.caption(
            "The model was optimized using GridSearchCV with 5-fold cross-validation "
            "and evaluated on a held-out test set. The final deployed model was "
            "retrained on the complete dataset using the selected hyperparameters."
        )

        st.subheader("Performance Metrics")
        col1d, col2d = st.columns(2)
        col1d.metric("Test R2", round(app1_metadata["test_r2"], 4))
        col2d.metric("Cross-Val R2 (Mean)", round(app1_metadata["cv_mean_r2"], 4))
        col3d, col4d = st.columns(2)
        col3d.metric("MAE (Test)", round(app1_metadata["mae"], 2))
        col4d.metric("RMSE (Test)", round(app1_metadata["rmse"], 2))

        st.divider()
        st.subheader("Model Comparison")

        comparison_df_a1 = pd.DataFrame(APP1_MODEL_COMPARISON)
        comparison_df_a1 = comparison_df_a1.sort_values(by="Test R2", ascending=False)

        def highlight_selected(row):
            if "Random Forest" in row["Model"]:
                return ["background-color: #1E2A3A"] * len(row)
            return [""] * len(row)

        styled_df_a1 = comparison_df_a1.style.apply(highlight_selected, axis=1)
        st.dataframe(styled_df_a1, width='stretch')

        col_left, col_right = st.columns(2)

        with col_left:
            fig_compare_a1 = px.bar(
                comparison_df_a1, x="Model", y="Test R2",
                title="Model Comparison (Test R2)", color="Model",
                color_discrete_sequence=model_colors
            )
            fig_compare_a1.update_layout(
                xaxis_title="Model", yaxis_title="Test R2", showlegend=False
            )
            apply_theme(fig_compare_a1)
            st.plotly_chart(fig_compare_a1, width='stretch')

        with col_right:
            comparison_radar_a1 = comparison_df_a1.copy()
            comparison_radar_a1["MAE_norm"] = (
                comparison_radar_a1["MAE"] / comparison_radar_a1["MAE"].max()
            )
            comparison_radar_a1["RMSE_norm"] = (
                comparison_radar_a1["RMSE"] / comparison_radar_a1["RMSE"].max()
            )
            fig_radar_a1 = go.Figure()
            for _, row in comparison_radar_a1.iterrows():
                fig_radar_a1.add_trace(go.Scatterpolar(
                    r=[row["Test R2"], 1 - row["MAE_norm"], 1 - row["RMSE_norm"]],
                    theta=["R2", "MAE (inverted)", "RMSE (inverted)"],
                    fill="toself", name=row["Model"]
                ))
            fig_radar_a1.update_layout(
                polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
                showlegend=True
            )
            apply_theme(fig_radar_a1, {"title": "Model Performance Radar"})
            st.plotly_chart(fig_radar_a1, width='stretch')

        st.divider()
        st.subheader("Tuned Hyperparameters")
        st.write(app1_metadata["best_params"])


@st.fragment
def _render_app1_section2_diagnostics(analytics_data, apply_theme):
    """
    Section 2: Advanced Regression Diagnostics
    Covers predicted vs actual, residuals, residual distribution,
    prediction uncertainty, feature importance, and cumulative importance.
    """
    with st.expander(
        ":material/troubleshoot: Advanced Regression Diagnostics",
        expanded=False
    ):
        a1 = analytics_data
        y_test_a1d = a1["y_test"]
        y_test_pred_a1d = a1["y_pred"]
        residuals_a1d = a1["residuals"]
        uncertainty_unc = a1["uncertainty"]
        grouped_importance_df_a1 = a1["grouped_importance"]
        importance_sorted_a1 = a1["importance_sorted"]

        col_avp, col_res = st.columns(2)

        with col_avp:
            fig_avp_a1 = go.Figure()
            fig_avp_a1.add_trace(go.Scatter(
                x=y_test_a1d, y=y_test_pred_a1d, mode="markers",
                name="Predictions",
                marker=dict(color="#3E7DE0", opacity=0.6)
            ))
            min_val_a1 = min(y_test_a1d.min(), y_test_pred_a1d.min())
            max_val_a1 = max(y_test_a1d.max(), y_test_pred_a1d.max())
            fig_avp_a1.add_trace(go.Scatter(
                x=[min_val_a1, max_val_a1],
                y=[min_val_a1, max_val_a1],
                mode="lines", name="Ideal Fit",
                line=dict(color="#EF4444", width=2)
            ))
            fig_avp_a1.update_layout(
                title="Predicted vs Actual Salary",
                xaxis_title="Actual Salary",
                yaxis_title="Predicted Salary"
            )
            apply_theme(fig_avp_a1)
            st.plotly_chart(fig_avp_a1, width='stretch')

        with col_res:
            fig_res_a1 = go.Figure()
            fig_res_a1.add_trace(go.Scatter(
                x=y_test_pred_a1d, y=residuals_a1d, mode="markers",
                marker=dict(color="#3E7DE0", opacity=0.6)
            ))
            fig_res_a1.add_hline(y=0, line_dash="dash", line_color="#EF4444")
            fig_res_a1.update_layout(
                title="Residuals vs Predicted Values",
                xaxis_title="Predicted Salary",
                yaxis_title="Residual (Actual - Predicted)"
            )
            apply_theme(fig_res_a1)
            st.plotly_chart(fig_res_a1, width='stretch')

        col_rdist, col_unc = st.columns(2)

        with col_rdist:
            fig_rdist_a1 = px.histogram(
                x=residuals_a1d, nbins=30,
                labels={"x": "Residual"},
                title="Distribution of Residuals",
                color_discrete_sequence=["#A78BFA"]
            )
            fig_rdist_a1.update_traces(
                marker_line_color="#1B2230", marker_line_width=0.8
            )
            fig_rdist_a1.update_layout(
                xaxis_title="Residual", yaxis_title="Count"
            )
            apply_theme(fig_rdist_a1)
            st.plotly_chart(fig_rdist_a1, width='stretch')

        with col_unc:
            fig_unc_a1 = px.histogram(
                x=uncertainty_unc, nbins=25,
                title="Distribution of Prediction Uncertainty Across Trees",
                labels={
                    "x": "Prediction Standard Deviation",
                    "y": "Count"
                },
                color_discrete_sequence=["#A78BFA"]
            )
            fig_unc_a1.update_traces(
                marker_line_color="#1B2230", marker_line_width=0.8
            )
            apply_theme(fig_unc_a1)
            st.plotly_chart(fig_unc_a1, width='stretch')

        st.divider()

        col_fi, col_cumul = st.columns(2)

        with col_fi:
            fig_fi_a1 = px.bar(
                grouped_importance_df_a1,
                x="Importance",
                y="Original_Feature",
                orientation="h",
                title="Feature Importance (Grouped Variables)",
                color="Importance",
                color_continuous_scale=[[0, "#1E4799"], [0.5, "#4F8EF7"], [1.0, "#38BDF8"]]
            )
            fig_fi_a1.update_coloraxes(showscale=False)
            apply_theme(fig_fi_a1)
            st.plotly_chart(fig_fi_a1, width='stretch')

        with col_cumul:
            fig_cumul_a1 = px.line(
                importance_sorted_a1,
                x=importance_sorted_a1.index + 1,
                y="Cumulative Importance",
                title="Cumulative Feature Importance",
                markers=True
            )
            fig_cumul_a1.update_layout(
                xaxis_title="Number of Features",
                yaxis_title="Cumulative Importance"
            )
            apply_theme(fig_cumul_a1)
            fig_cumul_a1.add_hline(y=0.80, line_dash="dash", line_color="#F59E0B")
            st.plotly_chart(fig_cumul_a1, width='stretch')


@st.fragment
def _render_app1_section3_classifier(
    app1_classifier_metadata,
    APP1_CLASSIFIER_MODEL_COMPARISON,
    apply_theme,
    model_colors,
):
    """
    Section 3: Salary Level Classification Model + Career Stage Clustering
    Covers classifier metrics, model comparison, confusion matrix,
    feature importance, clustering metrics, cluster distribution,
    cluster characteristics, experience vs salary scatter, PCA visualization,
    scaler info, and association rule mining.
    """
    with st.expander(
        ":material/category: Classification and Clustering Models",
        expanded=False
    ):

        # ---- Classification sub-section ----
        st.subheader(":material/bar_chart: Salary Level Classification Model")
        st.caption(
            "The classifier predicts salary level categories based on input features. "
            "It complements the regression model by providing an interpretable salary band."
        )

        col1e, col2e = st.columns(2)
        col1e.metric("Accuracy", round(app1_classifier_metadata.get("accuracy", 0), 4))
        col2e.metric("F1 Score (Macro)", round(app1_classifier_metadata.get("f1_macro", 0), 4))
        col3e, col4e = st.columns(2)
        col3e.metric("Precision (Macro)", round(app1_classifier_metadata.get("precision_macro", 0), 4))
        col4e.metric("Recall (Macro)", round(app1_classifier_metadata.get("recall_macro", 0), 4))

        st.divider()
        st.subheader("Classification Model Comparison")
        classifier_comparison_df_a1 = pd.DataFrame(APP1_CLASSIFIER_MODEL_COMPARISON)
        classifier_comparison_df_a1 = classifier_comparison_df_a1.sort_values(
            by="F1 Score", ascending=False
        )

        def highlight_selected_classifier(row):
            if "HistGradientBoosting" in row["Model"]:
                return ["background-color: #1E2A3A"] * len(row)
            return [""] * len(row)

        styled_cls_df_a1 = classifier_comparison_df_a1.style.apply(
            highlight_selected_classifier, axis=1
        )
        st.dataframe(styled_cls_df_a1, width='stretch')

        col_cls_bar, col_cls_cm = st.columns(2)

        with col_cls_bar:
            fig_cls_compare_a1 = px.bar(
                classifier_comparison_df_a1, x="Model", y="F1 Score",
                title="Classification Model Comparison (F1 Score)",
                color="Model", color_discrete_sequence=model_colors
            )
            fig_cls_compare_a1.update_layout(
                xaxis_title="Model", yaxis_title="F1 Score", showlegend=False
            )
            apply_theme(fig_cls_compare_a1)
            st.plotly_chart(fig_cls_compare_a1, width='stretch')

        with col_cls_cm:
            cm_a1 = np.array(
                app1_classifier_metadata.get(
                    "confusion_matrix",
                    [[0, 0, 0], [0, 0, 0], [0, 0, 0]]
                )
            )
            fig_cm_a1 = px.imshow(
                cm_a1,
                text_auto=True,
                labels=dict(x="Predicted Label", y="Actual Label", color="Count"),
                x=["Early Career Range", "Professional Range", "Executive Range"],
                y=["Early Career Range", "Professional Range", "Executive Range"],
                title="Salary Level Classification Confusion Matrix",
                color_continuous_scale="Blues"
            )
            apply_theme(fig_cm_a1)
            st.plotly_chart(fig_cm_a1, width='stretch')

        st.divider()
        st.subheader("Tuned Hyperparameters")
        st.write(app1_classifier_metadata["best_params"])

        st.divider()
        st.subheader("Feature Importance (Classifier)")
        importance_dict = app1_classifier_metadata.get("feature_importance", {})
        importance_cls_df_a1 = (
            pd.DataFrame(list(importance_dict.items()), columns=["Feature", "Importance"])
            .sort_values(by="Importance", ascending=False)
        )
        importance_cls_df_a1 = importance_cls_df_a1.iloc[::-1]
        fig_cls_imp_a1 = px.bar(
            importance_cls_df_a1.head(15),
            x="Importance", y="Feature",
            orientation="h",
            title="Feature Importances (Salary Level Classifier)",
            color="Importance",
            color_continuous_scale=[[0, "#1E4799"], [0.5, "#4F8EF7"], [1.0, "#38BDF8"]]
        )
        fig_cls_imp_a1.update_coloraxes(showscale=False)
        apply_theme(fig_cls_imp_a1)
        st.plotly_chart(fig_cls_imp_a1, width='stretch')


@st.fragment
def _render_app1_section4_clustering_assoc(
    app1_cluster_metadata,
    analytics_data,
    df_app1,
    assoc_rules,
    apply_theme,
):
    """
    Section 4: Career Stage Clustering and Association Rule Mining
    """
    with st.expander(
        ":material/hub: Clustering and Association Rule Mining",
        expanded=False
    ):
        a1 = analytics_data
        stage_map = app1_cluster_metadata.get("cluster_stage_mapping", {})

        # ---- Clustering sub-header ----
        st.subheader(":material/scatter_plot: Career Stage Clustering Model")
        st.caption(
            "This model segments individuals into career stages using KMeans clustering "
            "based on Years of Experience and Education Level. A derived Career Score "
            "feature enhances separation between progression levels."
        )

        col1c, col2c = st.columns(2)
        col1c.metric(
            "Silhouette Score",
            round(app1_cluster_metadata.get("silhouette_score", 0), 4)
        )
        col2c.metric(
            "Davies-Bouldin Score",
            round(app1_cluster_metadata.get("davies_bouldin_score", 0), 4)
        )

        st.divider()
        st.subheader("Model Configuration")
        config_df_cluster = pd.DataFrame({
            "Parameter": [
                "Model Type",
                "Training Dataset",
                "Dataset Shape",
                "Features Used",
                "Engineered Feature",
                "Number of Clusters"
            ],
            "Value": [
                str(app1_cluster_metadata.get("model_type")),
                str(app1_cluster_metadata.get("training_dataset")),
                str(app1_cluster_metadata.get("dataset_shape")),
                ", ".join(map(str, app1_cluster_metadata.get("features_used", []))),
                str(app1_cluster_metadata.get("engineered_feature")),
                str(app1_cluster_metadata.get("cluster_count"))
            ]
        })
        st.dataframe(config_df_cluster, width='stretch')

        st.divider()

        # Two-column layout for cluster distribution and exp vs salary scatter
        col_cdist, col_scatter = st.columns(2)

        with col_cdist:
            st.subheader("Cluster Distribution")
            cluster_sizes = app1_cluster_metadata.get("cluster_sizes", {})
            cluster_df = pd.DataFrame({
                "Cluster": list(cluster_sizes.keys()),
                "Count": list(cluster_sizes.values())
            })
            cluster_df["Career Stage"] = cluster_df["Cluster"].map(stage_map)
            fig_cluster_dist = px.bar(
                cluster_df,
                x="Career Stage", y="Count",
                title="Distribution of Career Stages",
                color="Career Stage",
                color_discrete_sequence=["#38BDF8", "#4F8EF7", "#A78BFA"]
            )
            fig_cluster_dist.update_xaxes(
                categoryorder="array",
                categoryarray=["Entry Stage", "Growth Stage", "Leadership Stage"]
            )
            apply_theme(fig_cluster_dist)
            st.plotly_chart(fig_cluster_dist, width='stretch')

        with col_scatter:
            st.subheader("Experience vs Salary by Career Stage")
            cluster_labels = a1["cluster_labels"]
            df_plot = df_app1.copy()
            df_plot["Career Stage"] = [
                stage_map.get(int(c), "Unknown") for c in cluster_labels
            ]
            fig_cluster_scatter = px.scatter(
                df_plot,
                x="Years of Experience", y="Salary",
                color="Career Stage",
                title="Experience vs Salary by Career Stage",
                color_discrete_sequence=["#38BDF8", "#4F8EF7", "#A78BFA"]
            )
            fig_cluster_scatter.update_traces(marker=dict(size=6, opacity=0.6))
            apply_theme(fig_cluster_scatter)
            st.plotly_chart(fig_cluster_scatter, width='stretch')

        st.divider()

        # PCA visualization and centroids side by side
        col_pca, col_centroids = st.columns(2)

        with col_pca:
            st.subheader("Cluster Visualization (PCA Projection)")
            X_pca_vis = a1["X_pca"]
            cluster_labels_vis = a1["cluster_labels"]
            centroids_pca = a1["centroids_pca"]
            stage_labels_vis = [
                stage_map.get(int(c), "Unknown") for c in cluster_labels_vis
            ]
            plot_df = pd.DataFrame({
                "PCA1": X_pca_vis[:, 0],
                "PCA2": X_pca_vis[:, 1],
                "Career Stage": stage_labels_vis
            })
            fig_cluster_pca = px.scatter(
                plot_df, x="PCA1", y="PCA2",
                color="Career Stage",
                title="Cluster Visualization (PCA Projection)",
                color_discrete_sequence=["#38BDF8", "#4F8EF7", "#A78BFA"],
            )
            centroid_labels = [
                stage_map.get(i, f"Cluster {i}") for i in range(len(centroids_pca))
            ]
            for i, (x, y) in enumerate(centroids_pca):
                fig_cluster_pca.add_trace(go.Scatter(
                    x=[x], y=[y],
                    mode="markers+text",
                    showlegend=False,
                    marker=dict(
                        symbol="x", size=14, color="#EF4444",
                        line=dict(width=2),
                    ),
                    text=[centroid_labels[i]],
                    textposition="top center",
                    name=f"Centroid: {centroid_labels[i]}"
                ))
            apply_theme(fig_cluster_pca)
            fig_cluster_pca.update_layout(legend=dict(orientation="h", y=-0.2))
            st.plotly_chart(fig_cluster_pca, width='stretch')

        with col_centroids:
            st.subheader("Cluster Characteristics")
            cluster_stats = app1_cluster_metadata.get("cluster_statistics", {})
            if cluster_stats:
                cluster_stats_df = pd.DataFrame(cluster_stats)
                cluster_stats_df["Cluster"] = cluster_stats_df.index
                cluster_stats_df["Career Stage"] = cluster_stats_df["Cluster"].map(stage_map)
                if "Years of Experience" in cluster_stats_df.columns:
                    cluster_stats_df = cluster_stats_df.sort_values("Years of Experience")
            else:
                cluster_stats_df = pd.DataFrame()
            st.dataframe(cluster_stats_df, width='stretch')

            st.divider()
            st.subheader("Cluster Centroids (Scaled Feature Space)")
            centroids = app1_cluster_metadata.get("cluster_centroids", {})
            if centroids:
                centroids_df = pd.DataFrame(centroids)
                centroids_df["Cluster"] = centroids_df.index
                centroids_df["Career Stage"] = centroids_df["Cluster"].map(stage_map)
            else:
                centroids_df = pd.DataFrame()
            st.dataframe(centroids_df, width='stretch')

            st.divider()
            st.subheader("Feature Scaling Parameters")
            scaler_df = pd.DataFrame({
                "Feature": ["Years of Experience", "Education Level", "Career Score"],
                "Mean": app1_cluster_metadata.get("scaler_mean", []),
                "Scale": app1_cluster_metadata.get("scaler_scale", [])
            })
            st.dataframe(scaler_df, width='stretch')

        # ---- Association Rule Mining sub-section ----
        st.divider()
        st.subheader(":material/schema: Association Rule Mining Model")
        st.caption(
            "The Apriori algorithm identifies frequent patterns and relationships between features "
            "such as education level, experience category, job group, and salary category. "
            "Rules are evaluated using support (frequency), confidence (reliability), "
            "and lift (strength of association)."
        )

        rules_df = assoc_rules.copy()
        rules_df = rules_df[rules_df["lift"] > 1]

        def clean_text(x):
            return (
                x.replace("Education_Category_", "")
                 .replace("Experience_Category_", "")
                 .replace("Salary_Category_", "")
                 .replace("Job_Group_", "")
                 .replace("Country_", "")
                 .replace("_", " ")
            )

        rules_df["antecedents"] = rules_df["antecedents"].apply(
            lambda x: ", ".join([clean_text(i) for i in x])
            if isinstance(x, list) else str(x)
        )
        rules_df["consequents"] = rules_df["consequents"].apply(
            lambda x: ", ".join([clean_text(i) for i in x])
            if isinstance(x, list) else str(x)
        )
        rules_df["rule"] = rules_df["antecedents"] + " \u2192 " + rules_df["consequents"]
        rules_df["support"] = rules_df["support"].round(3)
        rules_df["confidence"] = rules_df["confidence"].round(3)
        rules_df["lift"] = rules_df["lift"].round(3)
        rules_df = rules_df.sort_values(by="lift", ascending=False)

        col1r, col2r, col3r = st.columns(3)
        col1r.metric("Total Rules", len(rules_df))
        col2r.metric("Max Confidence", round(rules_df["confidence"].max(), 3))
        col3r.metric("Max Lift", round(rules_df["lift"].max(), 3))
        st.caption(
            "Higher lift (>1) indicates strong associations. "
            "Confidence represents rule reliability, while support reflects frequency in dataset."
        )

        st.divider()
        top_rules = rules_df.sort_values(by="lift", ascending=False).head(10)
        st.subheader("Top Association Rules (Ranked by Lift)")
        st.dataframe(
            top_rules[["rule", "support", "confidence", "lift"]],
            width='stretch'
        )

        col_lift_bar, col_scatter = st.columns(2)

        with col_lift_bar:
            st.subheader("Rule Strength Analysis (Lift)")
            fig_lift = px.bar(
                top_rules,
                x="lift", y="rule",
                orientation="h",
                title="Top Rules by Lift",
                color="lift",
                color_continuous_scale=[[0, "#1E4799"], [0.5, "#4F8EF7"], [1.0, "#38BDF8"]]
            )
            fig_lift.update_coloraxes(showscale=False)
            apply_theme(fig_lift)
            st.plotly_chart(fig_lift, width='stretch')

        with col_scatter:
            st.subheader("Support vs Confidence Distribution")
            fig_scatter = px.scatter(
                rules_df,
                x="support", y="confidence",
                size="lift",
                hover_data=["rule"],
                title="Support vs Confidence (Bubble size represents Lift)",
                color="lift",
                color_continuous_scale=[[0, "#1E4799"], [0.5, "#4F8EF7"], [1.0, "#38BDF8"]]
            )
            fig_scatter.update_coloraxes(showscale=False)
            apply_theme(fig_scatter)
            st.plotly_chart(fig_scatter, width='stretch')
            st.caption(
                "Most rules cluster at low support but high confidence, indicating strong "
                "but less frequent patterns. High-lift rules highlight meaningful associations "
                "between career attributes and salary categories."
            )


# ---------------------------------------------------------------------------
# App 2 Analytics sections
# ---------------------------------------------------------------------------

@st.fragment
def _render_app2_section1_regression(
    app2_metadata,
    APP2_MODEL_COMPARISON,
    apply_theme,
    model_colors,
):
    """
    Section 1: XGBoost Regression Model — Overview
    """
    with st.expander(
        ":material/monitoring: XGBoost Regression Model",
        expanded=True
    ):
        st.caption(
            "The salary prediction model uses an XGBoost regression model trained "
            "on the full dataset after evaluation using a held-out test split."
        )

        st.subheader("Model Performance Metrics")
        col1f, col2f, col3f = st.columns(3)
        col1f.metric("Test R2 (log scale)", f"{app2_metadata.get('test_r2_log_scale', 0):.4f}")
        col2f.metric("MAE (USD)", f"${app2_metadata.get('mae_usd', 0):,.0f}")
        col3f.metric("RMSE (USD)", f"${app2_metadata.get('rmse_usd', 0):,.0f}")

        st.divider()
        st.subheader("Model Comparison")
        comparison_df_a2 = pd.DataFrame(APP2_MODEL_COMPARISON)
        comparison_df_a2 = comparison_df_a2.sort_values(by="Test R2", ascending=False)
        st.dataframe(comparison_df_a2, width='stretch')

        st.subheader("Model Performance Comparison")
        fig_compare_a2 = px.bar(
            comparison_df_a2, x="Model", y="Test R2",
            color="Model", title="Model Comparison Based on Test R2",
            color_discrete_sequence=model_colors
        )
        fig_compare_a2.update_layout(
            xaxis_title="Model", yaxis_title="Test R2", showlegend=False
        )
        apply_theme(fig_compare_a2)
        st.plotly_chart(fig_compare_a2, width='stretch')

        st.divider()
        st.subheader("Model Configuration")
        config_df_a2 = pd.DataFrame({
            "Parameter": [
                "Model Type",
                "Dataset Size",
                "Trees (n_estimators)",
                "Max Depth",
                "Learning Rate",
                "Target Transformation"
            ],
            "Value": [
                str(app2_metadata.get("model_type")),
                str(app2_metadata.get("dataset_size")),
                str(app2_metadata.get("n_estimators")),
                str(app2_metadata.get("max_depth")),
                str(app2_metadata.get("learning_rate")),
                str(app2_metadata.get("target_transformation"))
            ]
        })
        st.dataframe(config_df_a2, width='stretch')


@st.fragment
def _render_app2_section2_diagnostics(analytics_data, apply_theme):
    """
    Section 2: Regression Diagnostics for App 2
    """
    with st.expander(
        ":material/troubleshoot: Regression Diagnostics",
        expanded=False
    ):
        y_raw_a2 = analytics_data["y_actual"]
        preds_full_a2 = analytics_data["y_pred"]
        residuals_a2d = analytics_data["residuals"]
        uncertainty_a2 = analytics_data["uncertainty"]

        col_avp, col_res = st.columns(2)

        with col_avp:
            fig_avp_a2 = go.Figure()
            fig_avp_a2.add_trace(go.Scatter(
                x=y_raw_a2, y=preds_full_a2, mode="markers",
                name="Predictions",
                marker=dict(color="#3E7DE0", opacity=0.6)
            ))
            min_val_a2 = min(y_raw_a2.min(), preds_full_a2.min())
            max_val_a2 = max(y_raw_a2.max(), preds_full_a2.max())
            fig_avp_a2.add_trace(go.Scatter(
                x=[min_val_a2, max_val_a2],
                y=[min_val_a2, max_val_a2],
                mode="lines", name="Ideal Fit",
                line=dict(color="#EF4444", width=2)
            ))
            fig_avp_a2.update_layout(
                title="Predicted vs Actual Salary",
                xaxis_title="Actual Salary",
                yaxis_title="Predicted Salary"
            )
            apply_theme(fig_avp_a2)
            st.plotly_chart(fig_avp_a2, width='stretch')

        with col_res:
            fig_res_a2 = go.Figure()
            fig_res_a2.add_trace(go.Scatter(
                x=preds_full_a2, y=residuals_a2d, mode="markers",
                marker=dict(color="#3E7DE0", opacity=0.6)
            ))
            fig_res_a2.add_hline(y=0, line_dash="dash", line_color="#EF4444")
            fig_res_a2.update_layout(
                title="Residuals vs Predicted Values",
                xaxis_title="Predicted Salary",
                yaxis_title="Residual (Actual - Predicted)"
            )
            apply_theme(fig_res_a2)
            st.plotly_chart(fig_res_a2, width='stretch')

        col_rdist, col_unc = st.columns(2)

        with col_rdist:
            fig_rdist_a2 = px.histogram(
                x=residuals_a2d, nbins=30,
                title="Distribution of Residuals",
                labels={"x": "Residual"},
                color_discrete_sequence=["#A78BFA"]
            )
            fig_rdist_a2.update_traces(
                marker_line_color="#1B2230", marker_line_width=0.8
            )
            fig_rdist_a2.update_layout(
                title="Distribution of Residuals",
                xaxis_title="Residual",
                yaxis_title="Count"
            )
            apply_theme(fig_rdist_a2)
            st.plotly_chart(fig_rdist_a2, width='stretch')

        with col_unc:
            fig_unc_a2 = px.histogram(
                x=uncertainty_a2, nbins=25,
                title="Distribution of Prediction Uncertainty",
                labels={
                    "x": "Prediction Standard Deviation",
                    "y": "Count"
                },
                color_discrete_sequence=["#A78BFA"]
            )
            fig_unc_a2.update_traces(
                marker_line_color="#1B2230", marker_line_width=0.8
            )
            apply_theme(fig_unc_a2)
            st.plotly_chart(fig_unc_a2, width='stretch')


@st.fragment
def _render_app2_section3_features(analytics_data, apply_theme):
    """
    Section 3: Feature Importance and SHAP Analysis for App 2
    """
    with st.expander(
        ":material/insights: Feature Importance and SHAP Analysis",
        expanded=False
    ):
        grouped_importance_a2 = analytics_data["grouped_importance"]
        shap_df_a2 = analytics_data["shap_top"]
        preds_distribution_a2 = analytics_data["pred_distribution"]

        col_grouped, col_pred_dist = st.columns(2)

        with col_grouped:
            st.subheader("Feature Importance by Category")
            fig_grouped_a2 = px.bar(
                grouped_importance_a2,
                x="importance", y="group",
                orientation="h",
                title="Grouped Feature Importance",
                color="importance",
                color_continuous_scale=[[0, "#1E4799"], [0.5, "#4F8EF7"], [1, "#38BDF8"]]
            )
            fig_grouped_a2.update_coloraxes(showscale=False)
            fig_grouped_a2.update_layout(
                yaxis=dict(autorange="reversed"),
                xaxis_title="Total Model Influence",
                yaxis_title="Feature Group"
            )
            apply_theme(fig_grouped_a2)
            st.plotly_chart(fig_grouped_a2, width='stretch')

        with col_pred_dist:
            st.subheader("Predicted Salary Distribution")
            fig_pred_dist_a2 = px.histogram(
                x=preds_distribution_a2, nbins=30,
                title="Distribution of Predicted Salaries",
                labels={"x": "Predicted Salary"},
                color_discrete_sequence=["#A78BFA"]
            )
            fig_pred_dist_a2.update_traces(
                marker_line_color="#1B2230", marker_line_width=0.8
            )
            apply_theme(fig_pred_dist_a2)
            st.plotly_chart(fig_pred_dist_a2, width='stretch')

        st.divider()
        st.subheader("Top Feature Drivers (SHAP Analysis)")
        st.caption(
            "SHAP values measure how strongly each feature influences the model's predictions. "
            "Higher values indicate stronger impact on predicted salary."
        )
        fig_shap_a2 = px.bar(
            shap_df_a2.head(15),
            x="SHAP Importance", y="Feature",
            orientation="h",
            color="SHAP Importance",
            color_continuous_scale=[[0, "#1E4799"], [0.5, "#4F8EF7"], [1, "#38BDF8"]],
            title="Top Features Influencing Salary Predictions"
        )
        fig_shap_a2.update_layout(
            yaxis=dict(autorange="reversed"),
            xaxis_title="Average |SHAP Value|",
            yaxis_title="Feature",
            coloraxis_showscale=False
        )
        apply_theme(fig_shap_a2)
        st.plotly_chart(fig_shap_a2, width='stretch')


# ---------------------------------------------------------------------------
# Main entry point — called from app_resume.py
# ---------------------------------------------------------------------------

def render_model_analytics_tab(
    is_app1,
    # App 1 resources (None when App 2 is active)
    app1_model=None,
    app1_metadata=None,
    app1_classifier_metadata=None,
    app1_salary_band_model=None,
    app1_cluster_metadata=None,
    app1_analytics_loader=None,
    assoc_rules=None,
    df_app1=None,
    APP1_MODEL_COMPARISON=None,
    APP1_CLASSIFIER_MODEL_COMPARISON=None,
    # App 2 resources (None when App 1 is active)
    app2_model=None,
    app2_metadata=None,
    app2_analytics_loader=None,
    APP2_MODEL_COMPARISON=None,
    # Shared helpers (injected to avoid double-import)
    apply_theme=None,
    model_colors=None,
    # PDF helpers
    cached_app1_model_analytics_pdf=None,
    cached_app2_model_analytics_pdf=None,
):
    """
    Top-level renderer for the Model Analytics tab.

    All resources are injected from the caller so that cached loaders
    are never re-invoked here, preventing resource waste.
    """

    st.header(":material/analytics: Model Analytics and Performance Evaluation")

    # ------------------------------------------------------------------
    # APP 1
    # ------------------------------------------------------------------
    if is_app1:
        a1 = app1_analytics_loader()

        _render_app1_section1_regression(
            app1_metadata=app1_metadata,
            APP1_MODEL_COMPARISON=APP1_MODEL_COMPARISON,
            apply_theme=apply_theme,
            model_colors=model_colors,
        )

        _render_app1_section2_diagnostics(
            analytics_data=a1,
            apply_theme=apply_theme,
        )

        _render_app1_section3_classifier(
            app1_classifier_metadata=app1_classifier_metadata,
            APP1_CLASSIFIER_MODEL_COMPARISON=APP1_CLASSIFIER_MODEL_COMPARISON,
            apply_theme=apply_theme,
            model_colors=model_colors,
        )

        _render_app1_section4_clustering_assoc(
            app1_cluster_metadata=app1_cluster_metadata,
            analytics_data=a1,
            df_app1=df_app1,
            assoc_rules=assoc_rules,
            apply_theme=apply_theme,
        )

        # Resume NLP section — shared, always visible
        _render_resume_nlp_section()

        st.divider()
        analytics_pdf_buffer_a1 = cached_app1_model_analytics_pdf(
            app1_metadata,
            APP1_MODEL_COMPARISON,
            app1_classifier_metadata,
            a1,
            app1_cluster_metadata,
            assoc_rules,
            app1_model,
            app1_salary_band_model
        )
        st.download_button(
            label="Download Model Analytics Report (PDF)",
            data=analytics_pdf_buffer_a1,
            file_name="model_analytics_report.pdf",
            mime="application/pdf",
            width='stretch'
        )

    # ------------------------------------------------------------------
    # APP 2
    # ------------------------------------------------------------------
    else:
        analytics_a2 = app2_analytics_loader()

        _render_app2_section1_regression(
            app2_metadata=app2_metadata,
            APP2_MODEL_COMPARISON=APP2_MODEL_COMPARISON,
            apply_theme=apply_theme,
            model_colors=model_colors,
        )

        _render_app2_section2_diagnostics(
            analytics_data=analytics_a2,
            apply_theme=apply_theme,
        )

        _render_app2_section3_features(
            analytics_data=analytics_a2,
            apply_theme=apply_theme,
        )

        # Resume NLP section — shared, always visible
        _render_resume_nlp_section()

        st.divider()
        analytics_pdf_buffer_a2 = cached_app2_model_analytics_pdf(
            app2_metadata,
            APP2_MODEL_COMPARISON,
            analytics_a2,
            app2_model
        )
        st.download_button(
            label="Download Model Analytics Report (PDF)",
            data=analytics_pdf_buffer_a2,
            file_name="model_analytics_report.pdf",
            mime="application/pdf",
            width='stretch'
        )